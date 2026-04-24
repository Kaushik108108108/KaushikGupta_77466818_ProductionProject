from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from app.db import fetch_one, fetch_all, execute_dml
from app.ai_service import generate_ai_recommendation
import csv
import io
import re
import requests as http_requests
from app.email_service import send_custom_email, send_high_risk_alert
from app import ml_service

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)

    return decorated


# ── HELPER: Trend Analysis ──
def calculate_trend(term1_score, term2_score, term3_score):
    diff1 = term2_score - term1_score
    diff2 = term3_score - term2_score

    if diff1 > 3 and diff2 > 3:
        return 'improving', '↑ Improving', 'Student is consistently improving each term.'
    elif diff1 < -3 and diff2 < -3:
        return 'declining', '↓ Declining', 'Student marks are dropping each term. Immediate attention needed.'
    elif diff1 > 3 and diff2 < -3:
        return 'unstable', '~ Unstable', 'Marks went up then dropped. Performance is inconsistent.'
    elif diff1 < -3 and diff2 > 3:
        return 'recovering', '↑ Recovering', 'Marks dropped in term 2 but recovered in term 3. Monitor closely.'
    else:
        return 'stable', '→ Stable', 'Performance is consistent across all terms.'


# ── HELPER: Risk Calculation (Step 2) ──
def calculate_final_risk(predicted_score, attendance_rate, complaint_count, due_amount, trend):
    if predicted_score >= 75:
        base_risk = 'low'
    elif predicted_score >= 55:
        base_risk = 'medium'
    else:
        base_risk = 'high'

    risk_flags = []
    if complaint_count >= 3:
        risk_flags.append('HIGH BEHAVIOR RISK')
    elif complaint_count >= 1:
        risk_flags.append('BEHAVIOR WARNING')

    if due_amount > 5000:
        risk_flags.append('HIGH FINANCIAL RISK')
    elif due_amount > 0:
        risk_flags.append('FINANCIAL WARNING')

    if attendance_rate < 65:
        risk_flags.append('CRITICAL ATTENDANCE')
    elif attendance_rate < 75:
        risk_flags.append('LOW ATTENDANCE')

    if predicted_score < 55:
        risk_flags.append('POOR ACADEMIC PERFORMANCE')

    if trend == 'declining':
        risk_flags.append('DECLINING TREND')
    elif trend == 'unstable':
        risk_flags.append('UNSTABLE TREND')

    high_flags = ['HIGH BEHAVIOR RISK', 'HIGH FINANCIAL RISK', 'CRITICAL ATTENDANCE', 'DECLINING TREND']

    if base_risk == 'low' and len(risk_flags) >= 2:
        final_risk = 'medium'
    elif base_risk == 'low' and any(f in risk_flags for f in high_flags):
        final_risk = 'medium'
    elif base_risk == 'medium' and len(risk_flags) >= 1:
        final_risk = 'high'
    else:
        final_risk = base_risk

    return final_risk, risk_flags


# ── HELPER: Grade from score ──
def get_grade(score):
    if score >= 85:
        return 'A'
    elif score >= 75:
        return 'B+'
    elif score >= 65:
        return 'B'
    elif score >= 55:
        return 'C+'
    elif score >= 45:
        return 'C'
    else:
        return 'F'


def _fmt_dt(value):
    if value is None:
        return ''
    try:
        return value.strftime('%b %d, %Y %I:%M %p')
    except AttributeError:
        return str(value)


def _next_prediction_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(SUBSTR(prediction_id, 5))), 0) + 1 AS next_id
        FROM predictions
        WHERE REGEXP_LIKE(prediction_id, '^PRD-[0-9]+$')
    """)
    return f"PRD-{int(row['next_id']):03d}"



def _next_complaint_id():
    row = fetch_one("""
        SELECT NVL(MAX(complaint_id), 0) + 1 AS next_id
        FROM complaints
    """)
    return int(row['next_id'])


def _next_email_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(SUBSTR(email_id, 5))), 0) + 1 AS next_id
        FROM email_logs
        WHERE REGEXP_LIKE(email_id, '^EML-[0-9]+$')
    """)
    return f"EML-{int(row['next_id']):03d}"


def _normalize_row(row):
    """Convert Oracle dictionary keys to lowercase for template compatibility."""
    if not row: return row
    return {k.lower(): v for k, v in row.items()}

def _next_report_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(SUBSTR(report_id, 5))), 0) + 1 AS next_id
        FROM reports
        WHERE REGEXP_LIKE(report_id, '^REP-[0-9]+$')
    """)
    if not row: return "REP-001"
    nxt = _normalize_row(row).get('next_id', 1)
    return f"REP-{int(nxt):03d}"


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    cls_filter = request.args.get('cls', '').strip()
    sec_filter = request.args.get('sec', '').strip()
    risk_filter = request.args.get('risk', '').strip()
    search_query = request.args.get('q', '').strip().lower()

    # class_level is stored as e.g. 'Class 10', and the HTML dropdown passes this exact value.
    cls_filter_val = cls_filter if cls_filter else None

    import math
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    stats = fetch_one("""
        SELECT
            COUNT(*) AS total,
            NVL(SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END), 0) AS high,
            NVL(SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END), 0) AS medium,
            NVL(SUM(CASE WHEN risk_level = 'low' THEN 1 ELSE 0 END), 0) AS low,
            NVL(ROUND(AVG(performance_index)), 0) AS avg_pi
        FROM students
    """) or {"total": 0, "high": 0, "medium": 0, "low": 0, "avg_pi": 0}

    # Count filtered total
    filtered_count_row = fetch_one("""
        SELECT COUNT(*) AS total_cnt
        FROM students
        WHERE (:cls IS NULL OR class_level = :cls)
          AND (:sec IS NULL OR section = :sec)
          AND (:risk IS NULL OR risk_level = :risk)
          AND (
                :search IS NULL
                OR LOWER(full_name) LIKE :search
                OR LOWER(student_id) LIKE :search
              )
    """, {
        "cls": cls_filter_val,
        "sec": sec_filter or None,
        "risk": risk_filter or None,
        "search": f"%{search_query}%" if search_query else None
    })
    total_filtered = int(filtered_count_row['total_cnt'] if filtered_count_row else 0)
    total_pages = math.ceil(total_filtered / per_page) if total_filtered > 0 else 1

    students = fetch_all("""
        SELECT
            student_id,
            full_name,
            class_level,
            section,
            performance_index,
            risk_level,
            attendance_rate,
            due_amount,
            complaint_count
        FROM students
        WHERE (:cls IS NULL OR class_level = :cls)
          AND (:sec IS NULL OR section = :sec)
          AND (:risk IS NULL OR risk_level = :risk)
          AND (
                :search IS NULL
                OR LOWER(full_name) LIKE :search
                OR LOWER(student_id) LIKE :search
              )
        ORDER BY student_id
        OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
    """, {
        "cls": cls_filter_val,
        "sec": sec_filter or None,
        "risk": risk_filter or None,
        "search": f"%{search_query}%" if search_query else None,
        "offset": offset,
        "per_page": per_page
    })

    # Fetch distinct classes and their sections dynamically from DB
    class_rows = fetch_all("""
        SELECT DISTINCT class_level
        FROM students
        ORDER BY class_level
    """)
    classes = [row['class_level'] for row in class_rows]

    section_rows = fetch_all("""
        SELECT DISTINCT class_level, section
        FROM students
        ORDER BY class_level, section
    """)
    class_sections = {}
    for row in section_rows:
        cl = str(row['class_level'])
        sec = row['section']
        if cl not in class_sections:
            class_sections[cl] = []
        if sec not in class_sections[cl]:
            class_sections[cl].append(sec)
    all_sections = sorted(set(row['section'] for row in section_rows))

    # Count high risk students for bulk email JS
    high_risk_count = int(stats.get('high', 0))

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        students=students,
        cls_filter=cls_filter,
        sec_filter=sec_filter,
        risk_filter=risk_filter,
        search_query=request.args.get('q', ''),
        classes=classes,
        class_sections=class_sections,
        all_sections=all_sections,
        high_risk_count=high_risk_count,
        page=page,
        total_pages=total_pages,
        total_filtered=total_filtered
    )


@admin_bp.route('/student/<student_id>')
@admin_required
def student_details(student_id):
    q = request.args.get('q', '').strip().lower()

    if q:
        match = fetch_one("""
            SELECT student_id
            FROM students
            WHERE LOWER(student_id) LIKE :q
               OR LOWER(full_name) LIKE :q
            FETCH FIRST 1 ROWS ONLY
        """, {"q": f"%{q}%"})

        if match:
            return redirect(url_for('admin.student_details', student_id=match['student_id']))

        flash(f'No student found matching "{request.args.get("q")}"', 'error')

    student = fetch_one("""
        SELECT
            student_id,
            full_name,
            class_level,
            section,
            email,
            guardian_name,
            guardian_email,
            phone_number,
            NVL(performance_index, 0) AS performance_index,
            risk_level,
            NVL(confidence_score, 0) AS confidence_score,
            NVL(due_amount, 0) AS due_amount,
            NVL(attendance_rate, 0) AS attendance_rate,
            NVL(complaint_count, 0) AS complaint_count
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    # School-wide average PI for the detail page
    avg_row = fetch_one("""
        SELECT ROUND(AVG(NVL(performance_index, 0))) AS school_avg FROM students
    """) or {"school_avg": 0}
    school_avg = int(avg_row["school_avg"])

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.dashboard'))


    complaints = fetch_all("""
        SELECT
            complaint_id,
            complaint_type,
            recorded_at,
            description,
            severity,
            status
        FROM complaints
        WHERE student_id = :sid
        ORDER BY recorded_at DESC
    """, {"sid": student_id})

    academic_record = fetch_all("""
        SELECT
            sub.subject_name,
            ar.attendance_rate,
            ar.term1_score,
            ar.term2_score,
            ar.term3_score,
            ar.predicted_score,
            ar.trend_label,
            ar.ai_recommendation
        FROM student_academic_records ar
        JOIN subjects sub
          ON sub.subject_id = ar.subject_id
        WHERE ar.student_id = :sid
        ORDER BY sub.subject_name
    """, {"sid": student_id})

    risk_flags_rows = fetch_all("""
        SELECT DISTINCT pf.flag_name
        FROM predictions p
        JOIN prediction_flags pf
          ON pf.prediction_id = p.prediction_id
        WHERE p.student_id = :sid
        ORDER BY pf.flag_name
    """, {"sid": student_id})

    latest_prediction = fetch_one("""
        SELECT
            trend,
            trend_label,
            trend_note
        FROM predictions
        WHERE student_id = :sid
        ORDER BY created_at DESC
        FETCH FIRST 1 ROWS ONLY
    """, {"sid": student_id}) or {
        "trend": "stable",
        "trend_label": "→ Stable",
        "trend_note": ""
    }

    detail = dict(student)
    detail["risk_flags"] = [r["flag_name"] for r in risk_flags_rows]
    detail["trend"] = latest_prediction["trend"]
    detail["trend_label"] = latest_prediction["trend_label"]
    detail["trend_note"] = latest_prediction["trend_note"]
    detail["complaint"] = [
        {
            "complaint_id": row["complaint_id"],
            "complaint_type": row["complaint_type"],
            "recorded_at": _fmt_dt(row["recorded_at"]),
            "description": row["description"],
            "severity": row["severity"],
            "status": row["status"],
        }
        for row in complaints
    ]
    detail["academic_record"] = academic_record

    return render_template(
        'admin/student_details.html',
        student=detail,
        school_avg=school_avg,
        search_query=request.args.get('q', '')
    )



@admin_bp.route('/student/<student_id>/log-complaint', methods=['POST'])
@admin_required
def log_complaint(student_id):
    complaint_type = request.form.get('complaint_type', '').strip()
    severity = request.form.get('severity', '').strip()
    description = request.form.get('description', '').strip()

    if not complaint_type or not severity or not description:
        flash('All fields are required.', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))

    complaint_id = _next_complaint_id()

    try:
        # Insert into complaints table
        execute_dml("""
            INSERT INTO complaints (
                complaint_id,
                student_id,
                complaint_type,
                severity,
                description,
                recorded_at,
                recorded_by_admin_id,
                status
            )
            VALUES (
                :cid, :sid, :ctype, :sev, :comp_desc, CURRENT_TIMESTAMP, :admin_id, 'OPEN'
            )
        """, {
            "cid": complaint_id,
            "sid": student_id,
            "ctype": complaint_type,
            "sev": severity,
            "comp_desc": description,
            "admin_id": session.get("admin_id")
        })

        # Update students table complaint_count
        execute_dml("""
            UPDATE students
            SET complaint_count = complaint_count + 1
            WHERE student_id = :sid
        """, {"sid": student_id})

        flash('Complaint logged successfully!', 'success')
    except Exception as e:
        flash(f'Error logging complaint: {str(e)}', 'error')

    return redirect(url_for('admin.student_details', student_id=student_id))


@admin_bp.route('/student/<student_id>/resolve-complaint/<int:complaint_id>', methods=['POST'])
@admin_required
def resolve_complaint(student_id, complaint_id):
    try:
        # Update complaint status
        execute_dml("""
            UPDATE complaints
            SET status = 'RESOLVED'
            WHERE complaint_id = :cid AND student_id = :sid
        """, {"cid": complaint_id, "sid": student_id})

        # Fetch student details for risk recalculation
        student = fetch_one("""
            SELECT
                NVL(performance_index, 0) AS pi,
                NVL(attendance_rate, 0) AS attendance,
                NVL(complaint_count, 0) AS complaints,
                NVL(due_amount, 0) AS dues
            FROM students
            WHERE student_id = :sid
        """, {"sid": student_id})

        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('admin.dashboard'))

        # Fetch latest trend
        pred = fetch_one("""
            SELECT trend FROM (
                SELECT trend FROM predictions
                WHERE student_id = :sid
                ORDER BY created_at DESC
            ) WHERE ROWNUM = 1
        """, {"sid": student_id})
        trend = pred['trend'] if pred else 'stable'

        # Decrement complaint_count (only if it was OPEN before, but we assume it was)
        new_complaint_count = max(0, student['complaints'] - 1)

        # Recalculate risk
        new_risk, _ = ml_service.calculate_final_risk(
            student['pi'],
            student['attendance'],
            new_complaint_count,
            student['dues'],
            trend
        )

        # Update student record
        execute_dml("""
            UPDATE students
            SET complaint_count = :comp_cnt,
                risk_level = :risk
            WHERE student_id = :sid
        """, {
            "comp_cnt": new_complaint_count,
            "risk": new_risk,
            "sid": student_id
        })

        flash(f'Complaint #{complaint_id} resolved! Risk level updated to {new_risk.upper()}.', 'success')
    except Exception as e:
        flash(f'Error resolving complaint: {str(e)}', 'error')

    return redirect(url_for('admin.student_details', student_id=student_id))


@admin_bp.route('/student/<student_id>/clear-dues', methods=['POST'])
@admin_required
def clear_dues(student_id):
    try:
        # Fetch current data for risk recalculation
        student = fetch_one("""
            SELECT
                NVL(performance_index, 0) AS pi,
                NVL(attendance_rate, 0) AS attendance,
                NVL(complaint_count, 0) AS complaints
            FROM students
            WHERE student_id = :sid
        """, {"sid": student_id})

        if not student:
            flash('Student not found.', 'error')
            return redirect(url_for('admin.dashboard'))

        # Fetch latest trend (query Oracle way)
        pred = fetch_one("""
            SELECT trend FROM (
                SELECT trend FROM predictions
                WHERE student_id = :sid
                ORDER BY created_at DESC
            ) WHERE ROWNUM = 1
        """, {"sid": student_id})
        trend = pred['trend'] if pred else 'stable'

        # Recalculate risk with due_amount = 0
        new_risk, _ = ml_service.calculate_final_risk(
            student['pi'],
            student['attendance'],
            student['complaints'],
            0, # Dues cleared
            trend
        )

        # Update DB
        execute_dml("""
            UPDATE students
            SET due_amount = 0,
                risk_level = :risk
            WHERE student_id = :sid
        """, {"risk": new_risk, "sid": student_id})

        flash(f'Outstanding dues for {student_id} have been cleared. Risk level updated to {new_risk.upper()}.', 'success')
    except Exception as e:
        flash(f'Error clearing dues: {str(e)}', 'error')

    return redirect(url_for('admin.student_details', student_id=student_id))


@admin_bp.route('/student/<student_id>/update', methods=['POST'])
@admin_required
def update_student(student_id):
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    class_level = request.form.get('class_level', '').strip()
    section = request.form.get('section', '').strip()
    guardian_name = request.form.get('guardian_name', '').strip()
    guardian_email = request.form.get('guardian_email', '').strip()
    
    try:
        attendance = float(request.form.get('attendance_rate', 0))
        dues = float(request.form.get('due_amount', 0))
    except (ValueError, TypeError):
        flash('Invalid numeric input for attendance or dues.', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))

    if not full_name or not email:
        flash('Full name and email are required.', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))

    if not re.match(r"^[A-Za-z\s]+$", full_name):
        flash('Wrong input for Full Name. Correct version: Should only contain letters and spaces.', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))

    if phone and not re.match(r"^\d{10}$", phone):
        flash('Wrong input for Phone Number. Correct version: Should contain exactly 10 digits.', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))

    if guardian_name and not re.match(r"^[A-Za-z\s]+$", guardian_name):
        flash('Wrong input for Guardian Name. Correct version: Should only contain letters and spaces.', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))

    try:
        # Fetch current data for risk recalculation
        student_data = fetch_one("""
            SELECT complaint_count, NVL(performance_index, 0) as pi 
            FROM students WHERE student_id = :sid
        """, {"sid": student_id})
        
        pred = fetch_one("""
            SELECT trend FROM (
                SELECT trend FROM predictions
                WHERE student_id = :sid
                ORDER BY created_at DESC
            ) WHERE ROWNUM = 1
        """, {"sid": student_id})
        
        complaint_count = student_data['complaint_count'] if student_data else 0
        curr_pi = student_data['pi'] if student_data else 0
        trend = pred['trend'] if pred else 'stable'

        # Recalculate risk
        new_risk, _ = ml_service.calculate_final_risk(
            curr_pi, 
            attendance, 
            complaint_count, 
            dues, 
            trend
        )

        execute_dml("""
            UPDATE students
            SET full_name = :name,
                email = :email,
                phone_number = :phone,
                class_level = :cls,
                section = :sec,
                guardian_name = :g_name,
                guardian_email = :g_email,
                attendance_rate = :att,
                due_amount = :dues,
                risk_level = :risk
            WHERE student_id = :sid
        """, {
            "name": full_name,
            "email": email,
            "phone": phone,
            "cls": class_level,
            "sec": section,
            "g_name": guardian_name,
            "g_email": guardian_email,
            "att": attendance,
            "dues": dues,
            "risk": new_risk,
            "sid": student_id
        })
        
        flash(f'Student {student_id} updated successfully! Risk level: {new_risk.upper()}', 'success')
    except Exception as e:
        flash(f'Error updating student: {str(e)}', 'error')

    return redirect(url_for('admin.student_details', student_id=student_id))


@admin_bp.route('/student/<student_id>/delete', methods=['POST'])
@admin_required
def delete_student(student_id):
    try:
        # Delete related records to maintain integrity
        # Oracle usually allows multiple DELETEs or manual cascades if not set in DB
        execute_dml("DELETE FROM prediction_flags WHERE prediction_id IN (SELECT prediction_id FROM predictions WHERE student_id = :sid)", {"sid": student_id})
        execute_dml("DELETE FROM predictions WHERE student_id = :sid", {"sid": student_id})
        execute_dml("DELETE FROM student_academic_records WHERE student_id = :sid", {"sid": student_id})
        execute_dml("DELETE FROM complaints WHERE student_id = :sid", {"sid": student_id})
        execute_dml("DELETE FROM email_logs WHERE student_id = :sid", {"sid": student_id})
        
        # Cleanup chat messages
        execute_dml("DELETE FROM chat_messages WHERE session_id IN (SELECT session_id FROM chat_sessions WHERE student_id = :sid)", {"sid": student_id})
        execute_dml("DELETE FROM chat_sessions WHERE student_id = :sid", {"sid": student_id})
        # Delete AI recommendations and Fee Dues
        execute_dml("DELETE FROM ai_recommendations WHERE student_id = :sid", {"sid": student_id})
        execute_dml("DELETE FROM student_fee_dues WHERE student_id = :sid", {"sid": student_id})

        # Finally delete student record
        execute_dml("DELETE FROM students WHERE student_id = :sid", {"sid": student_id})
        
        flash(f'Student {student_id} and all related data have been removed.', 'success')
        return redirect(url_for('admin.dashboard'))
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')
        return redirect(url_for('admin.student_details', student_id=student_id))


@admin_bp.route('/send-email', methods=['GET', 'POST'])
@admin_bp.route('/send-email/<student_id>', methods=['GET', 'POST'])
@admin_required
def send_email(student_id='STU-001'):
    student = fetch_one("""
        SELECT
            student_id,
            full_name,
            email,
            guardian_email,
            risk_level,
            NVL(performance_index, 0) AS performance_index,
            NVL(due_amount, 0) AS due_amount,
            NVL(attendance_rate, 0) AS attendance_rate
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()
        cc_email = request.form.get('cc_email', '').strip() or None

        if not subject or not body:
            flash('Subject and body are required.', 'error')
            return render_template('admin/send_email.html', student=student)

        template_row = fetch_one("""
            SELECT template_id
            FROM email_templates
            WHERE template_name = 'Custom Message'
            FETCH FIRST 1 ROWS ONLY
        """)

        execute_dml("""
            INSERT INTO email_logs (
                email_id,
                student_id,
                to_email,
                cc_email,
                template_id,
                subject,
                body,
                priority,
                status,
                created_by_admin_id,
                sent_at
            )
            VALUES (
                :email_id,
                :student_id,
                :to_email,
                :cc_email,
                :template_id,
                :subject,
                :body,
                'normal',
                'sent',
                :admin_id,
                CURRENT_TIMESTAMP
            )
        """, {
            "email_id": _next_email_id(),
            "student_id": student["student_id"],
            "to_email": student["email"],
            "cc_email": cc_email,
            "template_id": template_row["template_id"] if template_row else None,
            "subject": subject,
            "body": body,
            "admin_id": session.get("admin_id")
        })

        success, error_msg = send_custom_email(
            recipient=student["email"],
            subject=subject,
            body=body,
            cc=cc_email
        )
        
        # AJAX support: return JSON if requested
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if not success:
                return jsonify({"success": False, "message": f"Failed: {error_msg}"}), 400
            return jsonify({"success": True, "message": "Email sent successfully!"}), 200

        if not success:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": f"Failed: {error_msg}"}), 400
            flash(f'Failed to send email via SMTP: {error_msg}', 'error')
            return redirect(url_for('admin.send_email', student_id=student_id))

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({"success": True, "message": "Email sent successfully!"}), 200

        flash('Email sent successfully!', 'success')
        return render_template('admin/send_email.html', student=student)

    return render_template('admin/send_email.html', student=student)


@admin_bp.route('/predictions')
@admin_required
def predictions():
    import math
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page
    
    total_row = fetch_one("SELECT COUNT(DISTINCT prediction_id) as cnt FROM predictions")
    total_filtered = int(total_row['cnt'] if total_row else 0)
    total_pages = math.ceil(total_filtered / per_page) if total_filtered > 0 else 1

    predictions_rows = fetch_all("""
        WITH p_paged AS (
            SELECT
                prediction_id,
                student_id,
                full_name_snapshot AS full_name,
                class_level_snapshot AS class_level,
                subject_name_snapshot AS subject_name,
                term1_score,
                term2_score,
                term3_score,
                attendance_rate,
                complaint_count_snapshot AS complaint_count,
                due_amount_snapshot AS due_amount,
                predicted_score,
                risk_level,
                trend_label,
                grade,
                confidence_score,
                predicted_by_role AS predicted_by,
                created_at
            FROM predictions
            ORDER BY created_at DESC
            OFFSET :offset ROWS FETCH NEXT :per_page ROWS ONLY
        )
        SELECT 
            p.*,
            (SELECT LISTAGG(pf.flag_name, ' | ') WITHIN GROUP (ORDER BY pf.flag_name)
             FROM prediction_flags pf 
             WHERE pf.prediction_id = p.prediction_id) AS risk_flags
        FROM p_paged p
        ORDER BY p.created_at DESC
    """, {"offset": offset, "per_page": per_page})

    formatted_predictions = []
    for row in predictions_rows:
        item = dict(row)
        item["created_at"] = _fmt_dt(item["created_at"])
        item["risk_flags"] = item["risk_flags"] or ""
        formatted_predictions.append(item)

    students = fetch_all("""
        SELECT student_id, full_name
        FROM students
        ORDER BY student_id
    """)

    subjects_rows = fetch_all("""
        SELECT subject_name FROM subjects WHERE is_active = 'Y' ORDER BY subject_name
    """) or []
    subjects = [r['subject_name'] for r in subjects_rows]

    # Use exported model metadata when available; otherwise fall back to a DB-side proxy.
    accuracy_row = fetch_one("""
        SELECT
            CASE WHEN COUNT(*) = 0 THEN 0
            ELSE ROUND(
                SUM(CASE WHEN ABS(predicted_score - (term1_score + term2_score + term3_score) / 3) <= 10
                         THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 0)
            END AS accuracy
        FROM predictions
    """) or {"accuracy": 0}
    fallback_accuracy = int(accuracy_row["accuracy"])
    model_accuracy = ml_service.get_model_confidence_pct(fallback_accuracy)
    model_name = ml_service.get_model_display_name()
    metadata = ml_service.get_model_metadata()
    artifact_source = metadata.get("artifact_source", "formula_fallback")
    if artifact_source == "formula_fallback":
        model_metric_sub = "Fallback estimate until trained artifact is added"
    elif artifact_source == "bootstrap_synthetic_demo_replace_after_colab":
        model_metric_sub = "Model accuracy"
    else:
        model_metric_sub = f"Live model: {model_name}"

    return render_template(
        'admin/predictions.html',
        predictions=formatted_predictions,
        students=students,
        subjects=subjects,
        model_accuracy=model_accuracy,
        model_name=model_name,
        model_metric_sub=model_metric_sub,
        page=page,
        total_pages=total_pages,
        total_filtered=total_filtered
    )


@admin_bp.route('/predictions/run', methods=['POST'])
@admin_required
def run_prediction():
    try:
        student_id = request.form.get('student_id', '').strip()
        subject_name = request.form.get('subject_name', '').strip()
        term1_score = float(request.form.get('term1_score', 0))
        term2_score = float(request.form.get('term2_score', 0))
        term3_score = float(request.form.get('term3_score', 0))
        attendance_rate = float(request.form.get('attendance_rate', 0))
    except ValueError:
        flash('Invalid numeric input.', 'error')
        return redirect(url_for('admin.predictions'))

    student = fetch_one("""
        SELECT
            student_id,
            full_name,
            class_level,
            NVL(due_amount, 0) AS due_amount,
            NVL(complaint_count, 0) AS complaint_count
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.predictions'))

    subject_row = fetch_one("""
        SELECT subject_id, subject_name
        FROM subjects
        WHERE LOWER(subject_name) = LOWER(:sn)
        FETCH FIRST 1 ROWS ONLY
    """, {"sn": subject_name})
    if not subject_row:
        flash(f'Subject "{subject_name}" not found in database.', 'error')
        return redirect(url_for('admin.predictions'))

    due_amount = float(student.get('due_amount', 0) or 0)
    complaint_count = int(student.get('complaint_count', 0) or 0)

    prediction_bundle = ml_service.build_prediction_payload(
        attendance_rate=attendance_rate,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
        complaint_count=complaint_count,
        due_amount=due_amount,
        audience="admin",
    )

    predicted_score = prediction_bundle['predicted_score']
    trend = prediction_bundle['trend']
    trend_label = prediction_bundle['trend_label']
    trend_note = prediction_bundle['trend_note']
    final_risk = prediction_bundle['risk_level']
    risk_flags = prediction_bundle['risk_flags']
    grade = prediction_bundle['grade']
    pi_label = prediction_bundle['pi_label']
    confidence_score = prediction_bundle['confidence_score']
    prediction_id = _next_prediction_id()

    ai_recommendation = generate_ai_recommendation(
        student_name=student["full_name"],
        subject_name=subject_row["subject_name"],
        risk_level=final_risk,
        trend=trend,
        predicted_score=predicted_score,
        attendance_rate=attendance_rate,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
        due_amount=due_amount,
        audience="admin",
    )

    execute_dml("""
        INSERT INTO predictions (
            prediction_id,
            student_id,
            subject_id,
            subject_name_snapshot,
            full_name_snapshot,
            class_level_snapshot,
            term1_score,
            term2_score,
            term3_score,
            attendance_rate,
            complaint_count_snapshot,
            due_amount_snapshot,
            predicted_score,
            risk_level,
            trend,
            trend_label,
            trend_note,
            grade,
            performance_index_label,
            confidence_score,
            ai_recommendation,
            predicted_by_role,
            predicted_by_admin_id,
            created_at
        )
        VALUES (
            :prediction_id,
            :student_id,
            :subject_id,
            :subject_name,
            :full_name,
            :class_level,
            :term1_score,
            :term2_score,
            :term3_score,
            :attendance_rate,
            :complaint_count_snapshot,
            :due_amount_snapshot,
            :predicted_score,
            :risk_level,
            :trend,
            :trend_label,
            :trend_note,
            :grade,
            :performance_index_label,
            :confidence_score,
            :ai_recommendation,
            'Admin',
            :admin_id,
            CURRENT_TIMESTAMP
        )
    """, {
        "prediction_id": prediction_id,
        "student_id": student_id,
        "subject_id": subject_row['subject_id'],
        "subject_name": subject_row["subject_name"],
        "full_name": student["full_name"],
        "class_level": student["class_level"],
        "term1_score": term1_score,
        "term2_score": term2_score,
        "term3_score": term3_score,
        "attendance_rate": attendance_rate,
        "complaint_count_snapshot": complaint_count,
        "due_amount_snapshot": due_amount,
        "predicted_score": predicted_score,
        "risk_level": final_risk,
        "trend": trend,
        "trend_label": trend_label,
        "trend_note": trend_note,
        "grade": grade,
        "performance_index_label": pi_label,
        "confidence_score": confidence_score,
        "ai_recommendation": ai_recommendation,
        "admin_id": session.get("admin_id")
    })

    for flag in risk_flags:
        execute_dml("""
            INSERT INTO prediction_flags (prediction_id, flag_name)
            VALUES (:prediction_id, :flag_name)
        """, {
            "prediction_id": prediction_id,
            "flag_name": flag
        })

    ml_service.upsert_student_academic_record(
        student_id=student_id,
        subject_id=subject_row['subject_id'],
        attendance_rate=attendance_rate,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
        predicted_score=predicted_score,
        grade=grade,
        trend=trend,
        trend_label=trend_label,
        ai_recommendation=ai_recommendation,
    )
    ml_service.update_student_rollup(
        student_id=student_id,
        predicted_score=predicted_score,
        risk_level=final_risk,
        attendance_rate=attendance_rate,
        confidence_score=confidence_score,
        trend=trend,
        trend_label=trend_label,
        trend_note=trend_note,
    )

    flash(
        f'Prediction complete for {student["full_name"]} — {subject_row["subject_name"]} | '
        f'Score: {predicted_score}% | Grade: {grade} | Trend: {trend_label} | Risk: {final_risk.upper()} | Model: {prediction_bundle["model_name"]}',
        'prediction-success'
    )
    return redirect(url_for('admin.predictions'))


@admin_bp.route('/predictions/export')
@admin_required
def export_predictions():
    # Use a simpler query without broken GROUP BY. Using subquery for LISTAGG is faster and safer in Oracle.
    predictions_rows = fetch_all("""
        SELECT
            p.prediction_id,
            p.student_id,
            p.full_name_snapshot AS full_name,
            p.class_level_snapshot AS class_level,
            p.subject_name_snapshot AS subject_name,
            p.term1_score,
            p.term2_score,
            p.term3_score,
            p.attendance_rate,
            p.due_amount_snapshot AS due_amount,
            p.predicted_score,
            p.grade,
            p.trend_label,
            p.risk_level,
            p.confidence_score,
            p.predicted_by_role AS predicted_by,
            p.created_at,
            (SELECT LISTAGG(pf.flag_name, ' | ') WITHIN GROUP (ORDER BY pf.flag_name)
             FROM prediction_flags pf 
             WHERE pf.prediction_id = p.prediction_id) AS risk_flags
        FROM predictions p
        ORDER BY p.created_at DESC
    """)

    def generate():
        data = io.StringIO()
        writer = csv.writer(data)
        
        # Header
        writer.writerow([
            'Prediction ID', 'Student ID', 'Full Name', 'Class', 'Subject',
            'Term 1', 'Term 2', 'Term 3', 'Attendance Rate',
            'Due Amount', 'Predicted Score', 'Grade', 'Trend',
            'Risk Level', 'Risk Flags', 'Confidence', 'Run By', 'Date'
        ])
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)
        
        for p in predictions_rows:
            writer.writerow([
                p['prediction_id'],
                p['student_id'],
                p['full_name'],
                p['class_level'],
                p['subject_name'],
                p.get('term1_score', '—'),
                p.get('term2_score', '—'),
                p.get('term3_score', '—'),
                f"{p.get('attendance_rate', '—')}%",
                f"Rs.{p.get('due_amount', '—')}",
                f"{p['predicted_score']}%",
                p.get('grade', '—'),
                p.get('trend_label', '—'),
                p['risk_level'],
                p.get('risk_flags') or 'None',
                f"{p['confidence_score']}%",
                p['predicted_by'],
                _fmt_dt(p['created_at'])
            ])
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

    return Response(
        generate(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=predictions_export.csv'}
    )


@admin_bp.route('/reports')
@admin_required
def reports():
    import json
    report_stats = fetch_one("""
        SELECT
            (SELECT COUNT(*) FROM reports) AS reports_generated,
            (SELECT COUNT(*) FROM reports WHERE status IN ('DRAFT','REVIEW')) AS pending_reviews,
            (SELECT COUNT(*) FROM email_logs WHERE status = 'sent') AS emails_sent,
            (SELECT COUNT(*) FROM reports WHERE status = 'ESCALATED') AS escalations
        FROM dual
    """) or {"reports_generated": 0, "pending_reviews": 0, "emails_sent": 0, "escalations": 0}

    report_rows = fetch_all("""
        SELECT
            report_id,
            title,
            report_type,
            generated_by_type,
            status,
            TO_CHAR(created_at, 'Mon DD, YYYY') AS created_at_fmt
        FROM reports
        ORDER BY created_at DESC
        FETCH FIRST 20 ROWS ONLY
    """) or []
    report_rows = [_normalize_row(r) for r in report_rows]

    # Handle selective report view
    view_id = request.args.get('view_id')
    selected_report = None
    report_content = []
    report_params = {}

    if view_id:
        selected_report = fetch_one("SELECT * FROM reports WHERE report_id = :rid", {"rid": view_id})
        selected_report = _normalize_row(selected_report)
        
        if selected_report:
            try:
                # payload contains 'summary', 'details', and 'parameters'
                payload = json.loads(selected_report.get('description', '{}'))
                report_content = payload
                report_params = payload.get('parameters', {})
            except Exception:
                report_content = {}
                report_params = {}

    # Fetch classes for the generation modal
    cls_rows = [_normalize_row(r) for r in fetch_all("SELECT DISTINCT class_level FROM students ORDER BY class_level")]
    classes = [r['class_level'] for r in cls_rows]

    return render_template('admin/reports.html',
                           report_stats=_normalize_row(report_stats) if report_stats else {},
                           report_rows=report_rows,
                           classes=classes,
                           selected_report=selected_report,
                           report_content=report_content,
                           report_params=report_params)


@admin_bp.route('/reports/generate', methods=['POST'])
@admin_required
def generate_report():
    import json
    rtype = request.form.get('report_type', 'RISK').upper()
    cls = request.form.get('class_level', '').strip() or None
    d_start = request.form.get('date_start', '').strip() or None
    d_end = request.form.get('date_end', '').strip() or None

    title = f"{rtype.title()} Report"
    if cls: title += f" - {cls}"
    if d_start and d_end: title += f" ({d_start} to {d_end})"
    elif d_start: title += f" (from {d_start})"

    summary = []
    details = []
    params = {"cls": cls, "d_start": d_start, "d_end": d_end}

    try:
        if rtype == 'RISK':
            sql_sum = """
                SELECT risk_level, COUNT(*) as count, ROUND(AVG(performance_index), 1) as avg_pi
                FROM students
                WHERE (:cls IS NULL OR class_level = :cls)
                GROUP BY risk_level
                ORDER BY risk_level
            """
            sql_det = """
                SELECT student_id, full_name, risk_level, performance_index 
                FROM students 
                WHERE (:cls IS NULL OR class_level = :cls) 
                ORDER BY risk_level DESC, performance_index ASC
            """
            summary = [_normalize_row(r) for r in fetch_all(sql_sum, {"cls": cls})]
            details = [_normalize_row(r) for r in fetch_all(sql_det, {"cls": cls})]
        
        elif rtype == 'ACADEMIC':
            sql_sum = """
                SELECT class_level, section, ROUND(AVG(performance_index), 1) as avg_pi, COUNT(*) as total_students
                FROM students
                WHERE (:cls IS NULL OR class_level = :cls)
                GROUP BY class_level, section
                ORDER BY class_level, section
            """
            sql_det = """
                SELECT student_id, full_name, class_level, section, performance_index 
                FROM students 
                WHERE (:cls IS NULL OR class_level = :cls) 
                ORDER BY class_level, section, performance_index DESC
            """
            summary = [_normalize_row(r) for r in fetch_all(sql_sum, {"cls": cls})]
            details = [_normalize_row(r) for r in fetch_all(sql_det, {"cls": cls})]

        elif rtype == 'FINANCIAL':
            sql_sum = """
                SELECT class_level, SUM(due_amount) as total_dues, COUNT(CASE WHEN due_amount > 0 THEN 1 END) as students_with_dues
                FROM students
                WHERE (:cls IS NULL OR class_level = :cls)
                GROUP BY class_level
                ORDER BY total_dues DESC
            """
            sql_det = """
                SELECT student_id, full_name, class_level, due_amount 
                FROM students 
                WHERE (:cls IS NULL OR class_level = :cls) AND due_amount > 0
                ORDER BY due_amount DESC
            """
            summary = [_normalize_row(r) for r in fetch_all(sql_sum, {"cls": cls})]
            details = [_normalize_row(r) for r in fetch_all(sql_det, {"cls": cls})]

        elif rtype == 'BEHAVIOR':
            sql_sum = """
                SELECT complaint_type, severity, COUNT(*) as count
                FROM complaints c
                JOIN students s ON s.student_id = c.student_id
                WHERE (:cls IS NULL OR s.class_level = :cls)
                  AND (:d_start IS NULL OR c.recorded_at >= TO_TIMESTAMP(:d_start, 'YYYY-MM-DD'))
                  AND (:d_end IS NULL OR c.recorded_at <= TO_TIMESTAMP(:d_end, 'YYYY-MM-DD'))
                GROUP BY complaint_type, severity
                ORDER BY severity DESC, count DESC
            """
            sql_det = """
                SELECT s.student_id, s.full_name, s.class_level, c.complaint_type, c.severity, 
                       c.description, TO_CHAR(c.recorded_at, 'YYYY-MM-DD') as recorded_at
                FROM complaints c
                JOIN students s ON s.student_id = c.student_id
                WHERE (:cls IS NULL OR s.class_level = :cls)
                  AND (:d_start IS NULL OR c.recorded_at >= TO_TIMESTAMP(:d_start, 'YYYY-MM-DD'))
                  AND (:d_end IS NULL OR c.recorded_at <= TO_TIMESTAMP(:d_end, 'YYYY-MM-DD'))
                ORDER BY c.recorded_at DESC
            """
            summary = [_normalize_row(r) for r in fetch_all(sql_sum, {"cls": cls, "d_start": d_start, "d_end": d_end})]
            details = [_normalize_row(r) for r in fetch_all(sql_det, {"cls": cls, "d_start": d_start, "d_end": d_end})]

        report_id = _next_report_id()
        payload = {
            "parameters": params,
            "summary": summary,
            "details": details
        }

        execute_dml("""
            INSERT INTO reports (
                report_id, title, report_type, generated_by_type, generated_by_admin_id,
                status, created_at, description
            ) VALUES (
                :rid, :title, :rtype, 'ADMIN', :admin_id,
                'REVIEW', CURRENT_TIMESTAMP, :payload
            )
        """, {
            "rid": report_id,
            "title": title,
            "rtype": rtype,
            "admin_id": session.get("admin_id"),
            "payload": json.dumps(payload)
        })

        flash(f'Report "{title}" generated successfully!', 'report-success')
    except Exception as e:
        flash(f'Error generating report: {str(e)}', 'report-error')

    return redirect(url_for('admin.reports', view_id=report_id))


@admin_bp.route('/reports/status/<report_id>/<new_status>')
@admin_required
def update_report_status(report_id, new_status):
    new_status = new_status.upper()
    if new_status not in ['REVIEW', 'PUBLISHED', 'ESCALATED']:
        flash('Invalid status target.', 'error')
        return redirect(url_for('admin.reports', view_id=report_id))

    try:
        execute_dml(
            "UPDATE reports SET status = :status WHERE report_id = :rid",
            {"status": new_status, "rid": report_id}
        )
        flash(f'Report {report_id} status updated to {new_status}.', 'report-success')
    except Exception as e:
        flash(f'Database error: {str(e)}', 'report-error')

    return redirect(url_for('admin.reports', view_id=report_id))


@admin_bp.route('/reports/delete/<report_id>')
@admin_required
def delete_report(report_id):
    try:
        execute_dml("DELETE FROM reports WHERE report_id = :rid", {"rid": report_id})
        flash(f'Report {report_id} deleted successfully.', 'report-success')
    except Exception as e:
        flash(f'Error deleting report: {str(e)}', 'report-error')
    return redirect(url_for('admin.reports'))








@admin_bp.route('/save-draft/<student_id>', methods=['POST'])
@admin_required
def save_draft(student_id):
    subject = request.form.get('subject', '').strip()
    body = request.form.get('body', '').strip()
    cc_email = request.form.get('cc_email', '').strip() or None

    if not subject and not body:
        flash('Nothing to save as draft.', 'error')
        return redirect(url_for('admin.send_email', student_id=student_id))

    template_row = fetch_one("""
        SELECT template_id FROM email_templates
        WHERE template_name = 'Custom Message'
        FETCH FIRST 1 ROWS ONLY
    """)

    student = fetch_one("SELECT email, guardian_email FROM students WHERE student_id = :sid",
                        {"sid": student_id})
    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    execute_dml("""
        INSERT INTO email_logs (
            email_id, student_id, to_email, cc_email,
            template_id, subject, body, priority, status,
            created_by_admin_id
        ) VALUES (
            :email_id, :student_id, :to_email, :cc_email,
            :template_id, :subject, :body, 'normal', 'draft', :admin_id
        )
    """, {
        "email_id": _next_email_id(),
        "student_id": student_id,
        "to_email": student["email"],
        "cc_email": cc_email,
        "template_id": template_row["template_id"] if template_row else None,
        "subject": subject or "(No subject)",
        "body": body or "(No body)",
        "admin_id": session.get("admin_id"),
    })

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({"success": True, "message": "Draft saved successfully."}), 200
        
    flash('Draft saved successfully.', 'success')
    return redirect(url_for('admin.send_email', student_id=student_id))

@admin_bp.route('/bulk-email-high-risk', methods=['POST'])
@admin_required
def bulk_email_high_risk():
    """Send a warning email log entry for every high-risk student."""
    high_risk_students = fetch_all("""
        SELECT student_id, full_name, email, guardian_email
        FROM students
        WHERE risk_level = 'high'
          AND account_status = 'ACTIVE'
        ORDER BY student_id
    """)

    template_row = fetch_one("""
        SELECT template_id FROM email_templates
        WHERE template_name = 'High Risk Warning'
        FETCH FIRST 1 ROWS ONLY
    """)

    sent = 0
    for s in high_risk_students:
        try:
            execute_dml("""
                INSERT INTO email_logs (
                    email_id, student_id, to_email, cc_email,
                    template_id, subject, body, priority, status,
                    created_by_admin_id, sent_at
                ) VALUES (
                    :email_id, :student_id, :to_email, :cc_email,
                    :template_id,
                    'URGENT: High Risk Academic Alert — ' || :full_name,
                    'Dear ' || :full_name || ' and Guardian,' || CHR(10) ||
                    'This student has been flagged HIGH RISK by ScholarAI. Immediate intervention is recommended.',
                    'urgent', 'sent', :admin_id, CURRENT_TIMESTAMP
                )
            """, {
                "email_id": _next_email_id(),
                "student_id": s["student_id"],
                "to_email": s["email"],
                "cc_email": s.get("guardian_email"),
                "template_id": template_row["template_id"] if template_row else None,
                "full_name": s["full_name"],
                "admin_id": session.get("admin_id"),
            })
            
            success, error_msg = send_high_risk_alert(
                student_name=s["full_name"],
                recipient=s["email"],
                cc=s.get("guardian_email")
            )
            
            if success:
                sent += 1
            else:
                print(f"Failed to send bulk email to {s['email']}: {error_msg}")
                
        except Exception as e:
            print(f"Database log error for {s['email']}: {str(e)}")

    return jsonify({"sent": sent, "total": len(high_risk_students)})

@admin_bp.route('/chatbot')
@admin_required
def chatbot():
    admin_id = session.get("admin_id")
    sel_session_id = request.args.get('session_id')
    is_new = request.args.get('new') == 'true'

    if is_new:
        # Deactivate all sessions for this admin to force a new one on next message
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'N' 
            WHERE owner_role = 'ADMIN' AND admin_id = :admin_id
        """, {"admin_id": admin_id})
    elif sel_session_id:
        # Deactivate all, then activate the selected one for this admin
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'N' 
            WHERE owner_role = 'ADMIN' AND admin_id = :admin_id
        """, {"admin_id": admin_id})
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'Y' 
            WHERE session_id = :sid AND owner_role = 'ADMIN' AND admin_id = :admin_id
        """, {"sid": sel_session_id, "admin_id": admin_id})

    # Check for an active session to load its history
    active_session = fetch_one("""
        SELECT session_id
        FROM chat_sessions
        WHERE owner_role = 'ADMIN' AND admin_id = :admin_id AND is_active = 'Y'
        ORDER BY created_at DESC
        FETCH FIRST 1 ROWS ONLY
    """, {"admin_id": admin_id})

    active_messages = []
    if active_session:
        active_messages = fetch_all("""
            SELECT sender_type, message_text
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY message_id ASC
        """, {"session_id": active_session["session_id"]})

    chat_session = fetch_all("""
        SELECT
            cs.session_id,
            cs.session_label,
            TO_CHAR(cs.created_at, 'DD Mon, HH24:MI') AS session_date,
            (SELECT SUBSTR(cm.message_text, 1, 40)
             FROM chat_messages cm
             WHERE cm.session_id = cs.session_id AND cm.sender_type = 'USER'
             ORDER BY cm.message_id ASC
             FETCH FIRST 1 ROWS ONLY) AS topic
        FROM chat_sessions cs
        WHERE cs.owner_role = 'ADMIN' AND cs.admin_id = :admin_id
        ORDER BY cs.created_at DESC
        FETCH FIRST 20 ROWS ONLY
    """, {"admin_id": admin_id})

    return render_template('admin/chatbot.html', 
                           chat_session=chat_session, 
                           active_messages=active_messages,
                           active_session_id=active_session['session_id'] if active_session else None)


@admin_bp.route('/chatbot/delete/<session_id>')
@admin_required
def delete_chat_session(session_id):
    admin_id = session.get("admin_id")
    # Delete messages first (child rows), then the session
    execute_dml("""
        DELETE FROM chat_messages WHERE session_id = :sid
    """, {"sid": session_id})
    execute_dml("""
        DELETE FROM chat_sessions 
        WHERE session_id = :sid AND owner_role = 'ADMIN' AND admin_id = :admin_id
    """, {"sid": session_id, "admin_id": admin_id})
    return redirect(url_for('admin.chatbot'))


@admin_bp.route('/chatbot/send', methods=['POST'])
@admin_required
def chatbot_send():
    payload = request.get_json(silent=True) or {}
    msg = (payload.get('message') or '').strip()

    if not msg:
        return jsonify({'reply': 'Please enter a message.'}), 400

    admin_id = session.get("admin_id")

    session_row = fetch_one("""
        SELECT session_id, session_label
        FROM chat_sessions
        WHERE owner_role = 'ADMIN'
          AND admin_id = :admin_id
          AND is_active = 'Y'
        ORDER BY created_at DESC
        FETCH FIRST 1 ROWS ONLY
    """, {"admin_id": admin_id})

    if not session_row:
        import datetime
        execute_dml("""
            INSERT INTO chat_sessions (
                owner_role,
                admin_id,
                student_id,
                session_label,
                is_active
            )
            VALUES (
                'ADMIN',
                :admin_id,
                NULL,
                :slbl,
                'Y'
            )
        """, {
            "admin_id": admin_id,
            "slbl": f"Admin session - {datetime.datetime.now().strftime('%d %b, %H:%M')}"
        })

        session_row = fetch_one("""
            SELECT session_id, session_label
            FROM chat_sessions
            WHERE owner_role = 'ADMIN'
              AND admin_id = :admin_id
              AND is_active = 'Y'
            ORDER BY created_at DESC
            FETCH FIRST 1 ROWS ONLY
        """, {"admin_id": admin_id})


    # 1. Fetch live data context from existing tables
    try:
        # Overall stats
        stats = fetch_one("""
            SELECT COUNT(*) AS total,
                   ROUND(AVG(attendance_rate), 1) AS avg_att,
                   NVL(SUM(due_amount), 0) AS total_dues,
                   SUM(CASE WHEN risk_level = 'high'   THEN 1 ELSE 0 END) AS high_risk_cnt,
                   SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END) AS med_risk_cnt,
                   SUM(CASE WHEN risk_level = 'low'    THEN 1 ELSE 0 END) AS low_risk_cnt,
                   SUM(CASE WHEN due_amount > 0        THEN 1 ELSE 0 END) AS students_with_dues_cnt,
                   ROUND(AVG(NVL(performance_index, 0)), 1) AS avg_pi
            FROM students
        """)

        # High-risk students (fixed: lowercase 'high')
        high_risk_students = fetch_all("""
            SELECT full_name, student_id, class_level, section,
                   attendance_rate, NVL(performance_index, 0) AS pi,
                   NVL(due_amount, 0) AS due_amount, complaint_count
            FROM students
            WHERE risk_level = 'high'
            ORDER BY attendance_rate ASC
            FETCH FIRST 50 ROWS ONLY
        """)

        # Medium-risk students
        med_risk_students = fetch_all("""
            SELECT full_name, student_id, class_level, section,
                   attendance_rate, NVL(performance_index, 0) AS pi
            FROM students
            WHERE risk_level = 'medium'
            ORDER BY attendance_rate ASC
            FETCH FIRST 50 ROWS ONLY
        """)

        # Class-wise breakdown
        class_stats = fetch_all("""
            SELECT class_level,
                   COUNT(*) AS total,
                   SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_risk,
                   ROUND(AVG(attendance_rate), 1) AS avg_att,
                   ROUND(AVG(NVL(performance_index, 0)), 1) AS avg_pi
            FROM students
            GROUP BY class_level
            ORDER BY class_level
        """)

        # Subject-wise performance
        subject_perf = fetch_all("""
            SELECT s.subject_name,
                   COUNT(*) AS records,
                   ROUND(AVG(a.predicted_score), 1) AS avg_pred,
                   ROUND(AVG(a.attendance_rate), 1) AS avg_att,
                   SUM(CASE WHEN a.predicted_score < 50 THEN 1 ELSE 0 END) AS failing_count
            FROM student_academic_records a
            JOIN subjects s ON a.subject_id = s.subject_id
            GROUP BY s.subject_name
            ORDER BY avg_pred ASC
        """) or []

        # Prediction stats
        pred_stats = fetch_one("""
            SELECT COUNT(*) AS total_preds,
                   SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END) AS high_preds,
                   ROUND(AVG(predicted_score), 1) AS avg_pred_score
            FROM predictions
        """)

        # Open complaints summary
        complaint_stats = fetch_all("""
            SELECT complaint_type, COUNT(*) as cnt
            FROM complaints
            WHERE status = 'OPEN'
            GROUP BY complaint_type
            ORDER BY cnt DESC
        """)

        # Students with critical attendance < 75%
        low_att_students = fetch_all("""
            SELECT full_name, class_level, section, ROUND(attendance_rate, 1) AS att
            FROM students
            WHERE attendance_rate < 75
            ORDER BY attendance_rate ASC
            FETCH FIRST 50 ROWS ONLY
        """)

        # Students with significant dues
        dues_students = fetch_all("""
            SELECT full_name, class_level, NVL(due_amount, 0) AS due_amount
            FROM students
            WHERE due_amount > 0
            ORDER BY due_amount DESC
            FETCH FIRST 50 ROWS ONLY
        """)

        # Format data into compact strings
        high_risk_list = "\n".join([
            f"  - {s['full_name']} ({s['student_id']}) | Class: {s['class_level']}-{s['section']} | "
            f"Att: {s['attendance_rate']}% | PI: {s['pi']} | Dues: ₹{s['due_amount']} | Complaints: {s['complaint_count']}"
            for s in high_risk_students
        ]) or "  None"

        med_risk_list = "\n".join([
            f"  - {s['full_name']} ({s['student_id']}) | Class: {s['class_level']}-{s['section']} | Att: {s['attendance_rate']}% | PI: {s['pi']}"
            for s in med_risk_students
        ]) or "  None"

        class_list = "\n".join([
            f"  - {c['class_level']}: {c['total']} students | High Risk: {c['high_risk']} | Avg Att: {c['avg_att']}% | Avg PI: {c['avg_pi']}"
            for c in class_stats
        ]) or "  No class data."

        subject_list = "\n".join([
            f"  - {s['subject_name']}: Avg Predicted Score: {s['avg_pred']}% | Avg Att: {s['avg_att']}% | Failing (<50%): {s['failing_count']}"
            for s in subject_perf
        ]) or "  No subject data."

        comp_list = "\n".join([f"  - {c['complaint_type']}: {c['cnt']} open" for c in complaint_stats]) or "  No open complaints."

        low_att_list = "\n".join([
            f"  - {s['full_name']} ({s['class_level']}-{s['section']}): {s['att']}%"
            for s in low_att_students
        ]) or "  None"

        dues_list = "\n".join([
            f"  - {s['full_name']} ({s['class_level']}): ₹{s['due_amount']}"
            for s in dues_students
        ]) or "  None"

        system_prompt = f"""You are ScholarAI Admin Assistant — an AI embedded in a school management system.
You have DIRECT ACCESS to the following LIVE DATABASE snapshot. Use this data to answer all questions accurately and specifically.

=== SCHOOL OVERVIEW & COUNTS ===
- Total Enrolled Students: {stats['total'] if stats else 'N/A'}
- Risk Breakdown: {stats['high_risk_cnt'] if stats else 'N/A'} High Risk | {stats['med_risk_cnt'] if stats else 'N/A'} Medium Risk | {stats['low_risk_cnt'] if stats else 'N/A'} Low Risk
- Students with Pending Dues: {stats['students_with_dues_cnt'] if stats else 'N/A'}
- Average Performance Index: {stats['avg_pi'] if stats else 'N/A'}%
- Average Attendance: {stats['avg_att'] if stats else 'N/A'}%
- Total Outstanding Dues Amount: ₹{stats['total_dues'] if stats else '0'}
- Predictions Run: {pred_stats['total_preds'] if pred_stats else 'N/A'} (High Risk Found: {pred_stats['high_preds'] if pred_stats else 'N/A'})

=== HIGH-RISK STUDENTS ===
{high_risk_list}

=== MEDIUM-RISK STUDENTS ===
{med_risk_list}

=== CLASS-WISE BREAKDOWN ===
{class_list}

=== SUBJECT-WISE PERFORMANCE ===
{subject_list}

=== OPEN COMPLAINTS ===
{comp_list}

=== CRITICAL ATTENDANCE (<75%) ===
{low_att_list}

=== STUDENTS WITH OUTSTANDING DUES ===
{dues_list}

=== WEBSITE NAVIGATION GUIDE ===
- Dashboard (/admin/dashboard): View overview stats, filter students by class/section/risk, and view the main roster.
- Student Details (/admin/student/<student_id>): Access individual student data, update details, clear dues, log/resolve complaints, and send custom emails.
- Run New Prediction: Go to the Predictions page (/admin/predictions) from the sidebar navigation and click the "+ RUN NEW PREDICTION" button.
- Generate New Report: Go to the Reports page (/admin/reports) from the sidebar navigation and click the "+ GENERATE REPORT" button.
- Send Bulk Emails: On the Dashboard, click the "Email All High Risk" button.
- Send Custom Email: On the Dashboard, click the "EMAIL" button next to the student's name in the roster table. Alternatively, go to the Student Details page and click "Send Email".
- Update Student / Clear Dues: On the Student Details page, use the quick action buttons or "Edit Profile".

=== INSTRUCTIONS ===
- Answer questions using the exact data above. Name specific students when relevant.
- If asked about student counts (e.g. how many have dues, how many are medium risk), answer using the 'School Overview & Counts' section above!
- If asked about a student not listed, say they are not in the high/medium risk category.
- If asked "how to" do something or "where" a feature is on the website (like running predictions or reports), use the WEBSITE NAVIGATION GUIDE to give precise directions.
- When providing resources, advice, or video links to students or other admins, ONLY USE the exact links provided in the VERIFIED RESOURCE LIBRARY below. Do NOT make up or hallucinate any other URLs, as they will break.
- For management strategies, be concise and practical.
- Do NOT fabricate student names or numbers not shown above.
- Keep responses professional, clear, and structured.

=== VERIFIED RESOURCE LIBRARY ===
*Motivation & Study Habits (Exact Videos):*
- Tim Urban: Inside the mind of a master procrastinator - https://www.youtube.com/watch?v=arj7oStGLkU
- Angela Duckworth: Grit: the power of passion and perseverance - https://www.youtube.com/watch?v=H14bBuluwB8
- Ali Abdaal: How to study for exams - Evidence-based revision tips - https://www.youtube.com/watch?v=ukLnPbIffxE
- Matt D'Avella: How to stop procrastinating - https://www.youtube.com/watch?v=km4pOGd_lHw

*Academic Channels:*
- Khan Academy (Math/Science) - https://www.youtube.com/c/khanacademy
- CrashCourse (General Topics) - https://www.youtube.com/user/crashcourse
- MIT OpenCourseWare - https://www.youtube.com/c/mitocw"""

        # 2. Fetch history from existing chat_messages table
        history_rows = fetch_all("""
            SELECT sender_type, message_text 
            FROM chat_messages 
            WHERE session_id = :sid 
            ORDER BY message_id DESC 
            FETCH FIRST 6 ROWS ONLY
        """, {"sid": session_row["session_id"]})
        
        history_list = []
        for h in reversed(history_rows):
            history_list.append({
                "role": "user" if h["sender_type"] == "USER" else "assistant",
                "content": h["message_text"]
            })

    except Exception as e:
        print(f"Data context gathering error: {str(e)}")
        system_prompt = "You are ScholarAI Admin Assistant. Help with student data. (Context query failed)"
        history_list = []

    # Insert the user message AFTER history is fetched
    execute_dml("""
        INSERT INTO chat_messages (session_id, sender_type, message_text)
        VALUES (:session_id, 'USER', :message_text)
    """, {
        "session_id": session_row["session_id"],
        "message_text": msg
    })

    try:
        res = http_requests.post(
            "http://127.0.0.1:8000/chat",
            json={
                "message": msg,
                "history": history_list,
                "system_prompt": system_prompt
            },
            timeout=60
        )

        data = res.json()

        if not res.ok:
            reply = data.get('detail', 'FastAPI request failed.')
        else:
            reply = data.get('reply', 'No response from AI.')

    except Exception as e:
        reply = f'Connection error: {str(e)}'

    execute_dml("""
        INSERT INTO chat_messages (session_id, sender_type, message_text)
        VALUES (:session_id, 'BOT', :message_text)
    """, {
        "session_id": session_row["session_id"],
        "message_text": reply
    })

    return jsonify({
        'reply': reply,
        'session_id': session_row["session_id"]
    })