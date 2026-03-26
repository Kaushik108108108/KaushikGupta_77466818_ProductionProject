from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, Response
from app.db import fetch_one, fetch_all, execute_dml
import csv
import io

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


def _next_email_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(SUBSTR(email_id, 5))), 0) + 1 AS next_id
        FROM email_logs
        WHERE REGEXP_LIKE(email_id, '^EML-[0-9]+$')
    """)
    return f"EML-{int(row['next_id']):03d}"


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    cls_filter = request.args.get('cls', '').strip()
    sec_filter = request.args.get('sec', '').strip()
    risk_filter = request.args.get('risk', '').strip()
    search_query = request.args.get('q', '').strip().lower()

    stats = fetch_one("""
        SELECT
            COUNT(*) AS total,
            NVL(SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END), 0) AS high,
            NVL(SUM(CASE WHEN risk_level = 'medium' THEN 1 ELSE 0 END), 0) AS medium,
            NVL(ROUND(AVG(performance_index)), 0) AS avg_pi
        FROM students
    """) or {"total": 0, "high": 0, "medium": 0, "avg_pi": 0}

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
    """, {
        "cls": cls_filter or None,
        "sec": sec_filter or None,
        "risk": risk_filter or None,
        "search": f"%{search_query}%" if search_query else None
    })

    return render_template(
        'admin/dashboard.html',
        stats=stats,
        students=students,
        cls_filter=cls_filter,
        sec_filter=sec_filter,
        risk_filter=risk_filter,
        search_query=request.args.get('q', '')
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
            performance_index,
            risk_level,
            confidence_score,
            due_amount
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    complaints = fetch_all("""
        SELECT
            complaint_type,
            recorded_at,
            description,
            severity
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
            "complaint_type": row["complaint_type"],
            "recorded_at": _fmt_dt(row["recorded_at"]),
            "description": row["description"],
            "severity": row["severity"],
        }
        for row in complaints
    ]
    detail["academic_record"] = academic_record

    return render_template(
        'admin/student_details.html',
        student=detail,
        search_query=request.args.get('q', '')
    )


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
            risk_level
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        subject = request.form.get('subject', '').strip()
        body = request.form.get('body', '').strip()

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
            "cc_email": student["guardian_email"],
            "template_id": template_row["template_id"] if template_row else None,
            "subject": subject,
            "body": body,
            "admin_id": session.get("admin_id")
        })

        flash('Email sent successfully!', 'success')
        return redirect(url_for('admin.student_details', student_id=student_id))

    return render_template('admin/send_email.html', student=student)


@admin_bp.route('/predictions')
@admin_required
def predictions():
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
            p.complaint_count_snapshot AS complaint_count,
            p.due_amount_snapshot AS due_amount,
            p.predicted_score,
            p.risk_level,
            p.trend_label,
            p.grade,
            p.confidence_score,
            p.predicted_by_role AS predicted_by,
            p.created_at,
            LISTAGG(pf.flag_name, ' | ') WITHIN GROUP (ORDER BY pf.flag_name) AS risk_flags
        FROM predictions p
        LEFT JOIN prediction_flags pf
          ON pf.prediction_id = p.prediction_id
        GROUP BY
            p.prediction_id,
            p.student_id,
            p.full_name_snapshot,
            p.class_level_snapshot,
            p.subject_name_snapshot,
            p.term1_score,
            p.term2_score,
            p.term3_score,
            p.attendance_rate,
            p.complaint_count_snapshot,
            p.due_amount_snapshot,
            p.predicted_score,
            p.risk_level,
            p.trend_label,
            p.grade,
            p.confidence_score,
            p.predicted_by_role,
            p.created_at
        ORDER BY p.created_at DESC
    """)

    formatted_predictions = []
    for row in predictions_rows:
        item = dict(row)
        item["created_at"] = _fmt_dt(item["created_at"])
        item["risk_flags"] = item["risk_flags"] or ""
        formatted_predictions.append(item)

    students = fetch_all("""
        SELECT
            student_id,
            full_name,
            class_level,
            section,
            complaint_count,
            due_amount
        FROM students
        ORDER BY student_id
    """)

    return render_template(
        'admin/predictions.html',
        predictions=formatted_predictions,
        students=students
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
        complaint_count = int(request.form.get('complaint_count', 0))
        due_amount = float(request.form.get('due_amount', 0))
    except ValueError:
        flash('Invalid numeric input.', 'error')
        return redirect(url_for('admin.predictions'))

    student = fetch_one("""
        SELECT
            student_id,
            full_name,
            class_level
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    if not student:
        flash('Student not found.', 'error')
        return redirect(url_for('admin.predictions'))

    score_avg = (term1_score + term2_score + term3_score) / 3
    att_factor = (attendance_rate / 100) * 25
    predicted_score = round((score_avg * 0.75) + att_factor)
    predicted_score = max(0, min(100, predicted_score))

    trend, trend_label, trend_note = calculate_trend(term1_score, term2_score, term3_score)
    final_risk, risk_flags = calculate_final_risk(
        predicted_score, attendance_rate, complaint_count, due_amount, trend
    )
    grade = get_grade(predicted_score)
    prediction_id = _next_prediction_id()

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
            NULL,
            :subject_name,
            :full_name,
            :class_level,
            :term1_score,
            :term2_score,
            :term3_score,
            :attendance_rate,
            :complaint_count,
            :due_amount,
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
        "subject_name": subject_name,
        "full_name": student["full_name"],
        "class_level": student["class_level"],
        "term1_score": int(term1_score),
        "term2_score": int(term2_score),
        "term3_score": int(term3_score),
        "attendance_rate": attendance_rate,
        "complaint_count": complaint_count,
        "due_amount": due_amount,
        "predicted_score": predicted_score,
        "risk_level": final_risk,
        "trend": trend,
        "trend_label": trend_label,
        "trend_note": trend_note,
        "grade": grade,
        "performance_index_label": "Generated",
        "confidence_score": 82,
        "ai_recommendation": f"Generated for {subject_name}",
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

    flash(
        f'Prediction complete for {student["full_name"]} — {subject_name} | '
        f'Score: {predicted_score}% | Grade: {grade} | Trend: {trend_label} | Risk: {final_risk.upper()}',
        'success'
    )
    return redirect(url_for('admin.predictions'))


@admin_bp.route('/predictions/export')
@admin_required
def export_predictions():
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
            p.complaint_count_snapshot AS complaint_count,
            p.due_amount_snapshot AS due_amount,
            p.predicted_score,
            p.grade,
            p.trend_label,
            p.risk_level,
            p.confidence_score,
            p.predicted_by_role AS predicted_by,
            p.created_at,
            LISTAGG(pf.flag_name, ' | ') WITHIN GROUP (ORDER BY pf.flag_name) AS risk_flags
        FROM predictions p
        LEFT JOIN prediction_flags pf
          ON pf.prediction_id = p.prediction_id
        GROUP BY
            p.prediction_id,
            p.student_id,
            p.full_name_snapshot,
            p.class_level_snapshot,
            p.subject_name_snapshot,
            p.term1_score,
            p.term2_score,
            p.term3_score,
            p.attendance_rate,
            p.complaint_count_snapshot,
            p.due_amount_snapshot,
            p.predicted_score,
            p.grade,
            p.trend_label,
            p.risk_level,
            p.confidence_score,
            p.predicted_by_role,
            p.created_at
        ORDER BY p.created_at DESC
    """)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'Prediction ID', 'Student ID', 'Full Name', 'Class', 'Subject',
        'Term 1', 'Term 2', 'Term 3', 'Attendance Rate', 'Complaint Count',
        'Due Amount', 'Predicted Score', 'Grade', 'Trend',
        'Risk Level', 'Risk Flags', 'Confidence', 'Run By', 'Date'
    ])

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
            p.get('complaint_count', '—'),
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

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=predictions_export.csv'}
    )


@admin_bp.route('/reports')
@admin_required
def reports():
    return render_template('admin/reports.html')


@admin_bp.route('/chatbot')
@admin_required
def chatbot():
    chat_session = fetch_all("""
        SELECT
            session_id,
            session_label
        FROM chat_sessions
        WHERE (owner_role = 'ADMIN' AND admin_id = :admin_id)
           OR (owner_role = 'ADMIN' AND admin_id = 'ADM-001')
        ORDER BY created_at DESC
    """, {"admin_id": session.get("admin_id")})

    return render_template('admin/chatbot.html', chat_session=chat_session)


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
                'Admin support session',
                'Y'
            )
        """, {"admin_id": admin_id})

        session_row = fetch_one("""
            SELECT session_id, session_label
            FROM chat_sessions
            WHERE owner_role = 'ADMIN'
              AND admin_id = :admin_id
              AND is_active = 'Y'
            ORDER BY created_at DESC
            FETCH FIRST 1 ROWS ONLY
        """, {"admin_id": admin_id})

    execute_dml("""
        INSERT INTO chat_messages (session_id, sender_type, message_text)
        VALUES (:session_id, 'USER', :message_text)
    """, {
        "session_id": session_row["session_id"],
        "message_text": msg
    })

    msg_lower = msg.lower()

    if 'high risk' in msg_lower:
        count_row = fetch_one("""
            SELECT COUNT(*) AS total_high_risk
            FROM students
            WHERE risk_level = 'high'
        """)
        top_rows = fetch_all("""
            SELECT full_name, performance_index
            FROM students
            WHERE risk_level = 'high'
            ORDER BY performance_index ASC, full_name ASC
            FETCH FIRST 3 ROWS ONLY
        """)
        top_text = ', '.join(
            [f'{r["full_name"]} (PI:{r["performance_index"]}%)' for r in top_rows]
        ) or 'No students found.'
        reply = f'{count_row["total_high_risk"]} students are currently HIGH RISK. Top 3: {top_text}. Shall I draft emails?'

    elif 'attendance' in msg_lower:
        class_row = fetch_one("""
            SELECT
                class_level,
                section,
                ROUND(AVG(attendance_rate), 2) AS avg_att
            FROM students
            GROUP BY class_level, section
            ORDER BY avg_att ASC
            FETCH FIRST 1 ROWS ONLY
        """)

        low_row = fetch_one("""
            SELECT COUNT(*) AS low_count
            FROM students
            WHERE attendance_rate < 75
        """)

        if class_row:
            reply = (
                f'{class_row["class_level"]} Section {class_row["section"]} '
                f'has the lowest average attendance at {class_row["avg_att"]}%. '
                f'{low_row["low_count"]} students are below the 75% threshold.'
            )
        else:
            reply = 'No attendance data found.'

    else:
        reply = f'I received: "{msg}". Analyzing student database and prediction models...'

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
