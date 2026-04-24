import requests
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from app.db import fetch_one, fetch_all, execute_dml
from app.ai_service import generate_ai_recommendation
from app import ml_service

student_bp = Blueprint('student', __name__)


def student_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('student_logged_in'):
            return redirect(url_for('auth.student_login'))
        return f(*args, **kwargs)

    return decorated


# ── HELPER: Trend Analysis ──
def calculate_trend(term1_score, term2_score, term3_score):
    diff1 = term2_score - term1_score
    diff2 = term3_score - term2_score

    if diff1 > 3 and diff2 > 3:
        return 'improving', '↑ Improving', 'You are consistently improving each term. Keep it up!'
    elif diff1 < -3 and diff2 < -3:
        return 'declining', '↓ Declining', 'Your marks are dropping each term. Seek help immediately.'
    elif diff1 > 3 and diff2 < -3:
        return 'unstable', '~ Unstable', 'Marks went up then dropped. Try to maintain consistency.'
    elif diff1 < -3 and diff2 > 3:
        return 'recovering', '↑ Recovering', 'Marks dropped in term 2 but you recovered in term 3. Well done!'
    else:
        return 'stable', '→ Stable', 'Performance is consistent across all terms.'


# ── HELPER: Grade ──
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
        return value.strftime('%b %d, %Y')
    except AttributeError:
        return str(value)


def _next_prediction_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(SUBSTR(prediction_id, 5))), 0) + 1 AS next_id
        FROM predictions
        WHERE REGEXP_LIKE(prediction_id, '^PRD-[0-9]+$')
    """)
    return f"PRD-{int(row['next_id']):03d}"


def _get_student_dashboard_info(student_id):
    student = fetch_one("""
        SELECT
            student_id,
            full_name,
            REGEXP_REPLACE(class_level, '^Class[[:space:]]*', '') AS class_level,
            section,
            NVL(performance_index, 0) AS performance_index,
            NVL(risk_level, 'low') AS risk_level
        FROM students
        WHERE student_id = :sid
    """, {"sid": student_id})

    if not student:
        return None

    count_row = fetch_one("""
        SELECT COUNT(*) AS prediction_count
        FROM predictions
        WHERE student_id = :sid
    """, {"sid": student_id})

    student["performance_index"] = round(float(student["performance_index"]))
    student["prediction_count"] = int(count_row["prediction_count"]) if count_row else 0
    return student


def _build_ai_recommendation(subject_name, predicted_score, attendance_rate, trend,
                             student_name="Student", risk_level="medium",
                             term1_score=0, term2_score=0, term3_score=0):
    """Calls Anthropic API via ai_service; falls back to rule-based if key is missing."""
    return generate_ai_recommendation(
        student_name=student_name,
        subject_name=subject_name,
        risk_level=risk_level,
        trend=trend,
        predicted_score=predicted_score,
        attendance_rate=attendance_rate,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
        audience="student",
    )


# ── HELPER: rec_type badge from risk ──
def _rec_type(risk_level):
    return {'high': 'danger', 'medium': 'warning'}.get(risk_level, 'success')


@student_bp.route('/dashboard')
@student_required
def dashboard():
    sid = session.get('student_id')
    student_info = _get_student_dashboard_info(sid)

    if not student_info:
        flash('Student profile not found.', 'error')
        return redirect(url_for('auth.student_logout'))

    # Pull latest academic records for this student
    academic_rows = fetch_all("""
        SELECT
            sub.subject_name,
            ar.attendance_rate,
            ar.term1_score,
            ar.term2_score,
            ar.term3_score,
            NVL(ar.predicted_score, 0)      AS predicted_score,
            NVL(ar.trend, 'stable')         AS trend,
            NVL(ar.trend_label, '→ Stable') AS trend_label
        FROM student_academic_records ar
        JOIN subjects sub ON sub.subject_id = ar.subject_id
        WHERE ar.student_id = :sid
        ORDER BY sub.subject_name
    """, {"sid": sid})

    recs = []
    if academic_rows:
        # Generate a fresh AI recommendation for every subject
        for row in academic_rows:
            rec_text = _build_ai_recommendation(
                subject_name=row["subject_name"],
                predicted_score=float(row["predicted_score"]),
                attendance_rate=float(row["attendance_rate"]),
                trend=row["trend"],
                student_name=student_info["full_name"],
                risk_level=student_info["risk_level"],
                term1_score=float(row["term1_score"]),
                term2_score=float(row["term2_score"]),
                term3_score=float(row["term3_score"]),
            )
            recs.append({
                "subject_name": row["subject_name"],
                "recommendation_text": rec_text,
                "rec_type": _rec_type(student_info["risk_level"]),
            })
    else:
        # Fallback: use stored ai_recommendations table
        recs = fetch_all("""
            SELECT
                NVL(sub.subject_name, 'General') AS subject_name,
                recommendation_text,
                rec_type
            FROM ai_recommendations ar
            LEFT JOIN subjects sub ON sub.subject_id = ar.subject_id
            WHERE ar.student_id = :sid
              AND ar.is_active = 'Y'
            ORDER BY ar.created_at DESC
        """, {"sid": sid})

        if not recs:
            recs = [{
                "subject_name": "General",
                "recommendation_text": "Keep practicing consistently and maintain regular attendance.",
                "rec_type": "success"
            }]

    # Fetch subjects dynamically for the prediction form
    subject_rows = fetch_all("""
        SELECT subject_name FROM subjects WHERE is_active = 'Y' ORDER BY subject_name
    """) or []
    subjects = [r['subject_name'] for r in subject_rows]

    # Get any pending prediction result from session
    last_pred = session.pop('last_prediction', None)
    result = last_pred.get('result') if last_pred else None
    recs = last_pred.get('recs') if last_pred else []
    subject_name = last_pred.get('subject_name') if last_pred else None

    return render_template('student/dashboard.html',
                           student=student_info,
                           recs=recs,
                           result=result,
                           subject_name=subject_name,
                           subjects=subjects)


@student_bp.route('/predict', methods=['POST'])
@student_required
def predict():
    sid = session.get('student_id')

    try:
        term1_score = float(request.form.get('t1', 0))
        term2_score = float(request.form.get('t2', 0))
        term3_score = float(request.form.get('t3', 0))
        attendance_rate = float(request.form.get('attendance', 0))
    except ValueError:
        flash('Please enter valid numeric values.', 'error')
        return redirect(url_for('student.dashboard'))

    subject_name = (request.form.get('subject') or '').strip()
    if not subject_name:
        flash('Subject is required.', 'error')
        return redirect(url_for('student.dashboard'))

    student_row = fetch_one("""
        SELECT
            student_id,
            full_name,
            class_level,
            section,
            NVL(performance_index, 0) AS performance_index,
            NVL(risk_level, 'low') AS risk_level,
            NVL(complaint_count, 0) AS complaint_count,
            NVL(due_amount, 0) AS due_amount
        FROM students
        WHERE student_id = :sid
    """, {"sid": sid})

    if not student_row:
        flash('Student not found.', 'error')
        return redirect(url_for('auth.student_logout'))

    subject_row = fetch_one("""
        SELECT subject_id, subject_name
        FROM subjects
        WHERE LOWER(subject_name) = LOWER(:subject_name)
        FETCH FIRST 1 ROWS ONLY
    """, {"subject_name": subject_name})

    if not subject_row:
        flash('Selected subject was not found in the database.', 'error')
        return redirect(url_for('student.dashboard'))

    prediction_bundle = ml_service.build_prediction_payload(
        attendance_rate=attendance_rate,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
        complaint_count=int(student_row.get('complaint_count', 0) or 0),
        due_amount=float(student_row.get('due_amount', 0) or 0),
        audience="student",
    )

    predicted_score = prediction_bundle['predicted_score']
    trend = prediction_bundle['trend']
    trend_label = prediction_bundle['trend_label']
    trend_note = prediction_bundle['trend_note']
    risk_level = prediction_bundle['risk_level']
    risk_flags = prediction_bundle['risk_flags']
    grade = prediction_bundle['grade']
    pi_label = prediction_bundle['pi_label']
    confidence_score = prediction_bundle['confidence_score']
    prediction_id = _next_prediction_id()

    recommendation_text = _build_ai_recommendation(
        subject_name=subject_name,
        predicted_score=predicted_score,
        attendance_rate=attendance_rate,
        trend=trend,
        student_name=student_row["full_name"],
        risk_level=risk_level,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
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
            'Student',
            NULL,
            CURRENT_TIMESTAMP
        )
    """, {
        "prediction_id": prediction_id,
        "student_id": sid,
        "subject_id": subject_row["subject_id"],
        "subject_name": subject_row["subject_name"],
        "full_name": student_row["full_name"],
        "class_level": student_row["class_level"],
        "term1_score": term1_score,
        "term2_score": term2_score,
        "term3_score": term3_score,
        "attendance_rate": attendance_rate,
        "complaint_count_snapshot": int(student_row.get('complaint_count', 0) or 0),
        "due_amount_snapshot": float(student_row.get('due_amount', 0) or 0),
        "predicted_score": predicted_score,
        "risk_level": risk_level,
        "trend": trend,
        "trend_label": trend_label,
        "trend_note": trend_note,
        "grade": grade,
        "performance_index_label": pi_label,
        "confidence_score": confidence_score,
        "ai_recommendation": recommendation_text,
    })

    for flag in risk_flags:
        execute_dml("""
            INSERT INTO prediction_flags (prediction_id, flag_name)
            VALUES (:prediction_id, :flag_name)
        """, {"prediction_id": prediction_id, "flag_name": flag})

    ml_service.upsert_student_academic_record(
        student_id=sid,
        subject_id=subject_row['subject_id'],
        attendance_rate=attendance_rate,
        term1_score=term1_score,
        term2_score=term2_score,
        term3_score=term3_score,
        predicted_score=predicted_score,
        grade=grade,
        trend=trend,
        trend_label=trend_label,
        ai_recommendation=recommendation_text,
    )
    ml_service.update_student_rollup(
        student_id=sid,
        predicted_score=predicted_score,
        risk_level=risk_level,
        attendance_rate=attendance_rate,
        confidence_score=confidence_score,
        trend=trend,
        trend_label=trend_label,
        trend_note=trend_note,
    )

    student_info = _get_student_dashboard_info(sid)

    recs = [{
        "subject_name": subject_name,
        "recommendation_text": recommendation_text,
        "rec_type": _rec_type(risk_level),
    }]

    result = {
        'predicted_score': predicted_score,
        'grade': grade,
        'pi_label': pi_label,
        'risk_level': risk_level,
        'confidence_score': confidence_score,
        'trend': trend,
        'trend_label': trend_label,
        'trend_note': trend_note,
        'ai_recommendation': recommendation_text,
        'model_name': prediction_bundle['model_name'],
    }

    session['last_prediction'] = {
        'result': result,
        'recs': recs,
        'subject_name': subject_name
    }
    return redirect(url_for('student.dashboard'))


@student_bp.route('/activity' )
@student_required
def activity():
    sid = session.get('student_id')

    # Filter params from search form
    f_subject = request.args.get('subject', '').strip()
    f_risk    = request.args.get('risk', '').strip()

    history = fetch_all("""
        SELECT
            prediction_id,
            created_at,
            subject_name_snapshot AS subject_name,
            predicted_score,
            grade,
            NVL(performance_index_label, 'Generated') AS performance_index,
            risk_level,
            NVL(ai_recommendation, 'No recommendation available.') AS ai_recommendation
        FROM predictions
        WHERE student_id = :sid
          AND (:subject IS NULL OR LOWER(subject_name_snapshot) = LOWER(:subject))
          AND (:risk    IS NULL OR risk_level = :risk)
        ORDER BY created_at DESC
    """, {
        "sid": sid,
        "subject": f_subject or None,
        "risk":    f_risk or None,
    })

    formatted_history = []
    for row in history:
        item = dict(row)
        item["created_at"] = _fmt_dt(item["created_at"])
        try:
            item["predicted_score"] = round(float(item["predicted_score"]))
        except Exception:
            pass
        formatted_history.append(item)

    total = len(formatted_history)
    high_risk = sum(1 for p in formatted_history if p['risk_level'] == 'high')
    avg_score = round(sum(float(p['predicted_score']) for p in formatted_history) / total) if total else 0
    best_subject = max(formatted_history, key=lambda p: float(p['predicted_score']))['subject_name'] if total else '--'

    stats = {
        'total': total,
        'high_risk': high_risk,
        'avg_score': avg_score,
        'best_subject': best_subject
    }

    # Dynamic subjects list for search dropdown
    subject_rows = fetch_all("""
        SELECT subject_name FROM subjects WHERE is_active = 'Y' ORDER BY subject_name
    """) or []
    subjects = [r['subject_name'] for r in subject_rows]

    return render_template(
        'student/activity.html',
        history=formatted_history,
        stats=stats,
        subjects=subjects,
        f_subject=f_subject,
        f_risk=f_risk
    )


@student_bp.route('/chatbot')
@student_required
def chatbot():
    name = session.get('student_name', 'Student')
    sid = session.get('student_id', 'STU-001')
    sel_session_id = request.args.get('session_id')
    is_new = request.args.get('new') == 'true'

    if is_new:
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'N' 
            WHERE owner_role = 'STUDENT' AND student_id = :sid
        """, {"sid": sid})
    elif sel_session_id:
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'N' 
            WHERE owner_role = 'STUDENT' AND student_id = :sid
        """, {"sid": sid})
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'Y' 
            WHERE session_id = :session_id AND owner_role = 'STUDENT' AND student_id = :sid
        """, {"session_id": sel_session_id, "sid": sid})

    # Check for an active session to load its history
    active_session = fetch_one("""
        SELECT session_id
        FROM chat_sessions
        WHERE owner_role = 'STUDENT' AND student_id = :sid AND is_active = 'Y'
        ORDER BY created_at DESC
        FETCH FIRST 1 ROWS ONLY
    """, {"sid": sid})

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
            session_id,
            session_label
        FROM chat_sessions
        WHERE owner_role = 'STUDENT'
          AND student_id = :sid
        ORDER BY created_at DESC
        FETCH FIRST 20 ROWS ONLY
    """, {"sid": sid})

    return render_template(
        'student/chatbot.html',
        student_name=name,
        student_id=sid,
        chat_session=chat_session,
        active_messages=active_messages,
        active_session_id=active_session['session_id'] if active_session else None
    )


@student_bp.route('/chatbot/send', methods=['POST'])
@student_required
def chatbot_send():
    payload = request.get_json(silent=True) or {}
    msg = (payload.get('message') or '').strip()

    if not msg:
        return jsonify({'reply': 'Please enter a message.'}), 400

    sid = session.get('student_id')
    name = session.get('student_name', 'Student')

    session_row = fetch_one("""
        SELECT session_id
        FROM chat_sessions
        WHERE owner_role = 'STUDENT'
          AND student_id = :sid
          AND is_active = 'Y'
        ORDER BY created_at DESC
        FETCH FIRST 1 ROWS ONLY
    """, {"sid": sid})

    if not session_row:
        execute_dml("""
            INSERT INTO chat_sessions (
                owner_role, admin_id, student_id, session_label, is_active
            ) VALUES (
                'STUDENT', NULL, :student_id, :session_label, 'Y'
            )
        """, {
            "student_id": sid,
            "session_label": "Student learning support chat"
        })

        session_row = fetch_one("""
            SELECT session_id
            FROM chat_sessions
            WHERE owner_role = 'STUDENT'
              AND student_id = :sid
              AND is_active = 'Y'
            ORDER BY created_at DESC
            FETCH FIRST 1 ROWS ONLY
        """, {"sid": sid})



    # 1. Fetch student context
    try:
        student = fetch_one("""
            SELECT performance_index, risk_level, attendance_rate, due_amount, complaint_count
            FROM students WHERE student_id = :sid
        """, {"sid": sid})
        
        # Latest subject performance
        academic_summary = fetch_all("""
            SELECT sub.subject_name, ar.predicted_score, ar.trend_label
            FROM student_academic_records ar
            JOIN subjects sub ON sub.subject_id = ar.subject_id
            WHERE ar.student_id = :sid
            ORDER BY ar.predicted_score ASC
            FETCH FIRST 3 ROWS ONLY
        """, {"sid": sid})
        
        perf_list = "\n".join([f"- {a['subject_name']}: {a['predicted_score']}% ({a['trend_label']})" for a in academic_summary])
        
        system_prompt = f"""
            You are ScholarAI Student Assistant. You are chatting with {name} (ID: {sid}).
            Ground your answers in their personal data:
            - Performance Index: {student['performance_index'] if student else 0}%
            - Risk Level: {student['risk_level'] if student else 'Low'}
            - Attendance Rate: {student['attendance_rate'] if student else 0}%
            - Pending Dues: ₹{student['due_amount'] if student else 0}
            - Open Complaints: {student['complaint_count'] if student else 0}
            
            Their weak subjects needing attention:
            {perf_list if academic_summary else 'No data yet.'}
            
            Be helpful, encouraging, and clear. 
            When providing resources for motivation, study habits, or academics, ONLY USE the exact links provided in the VERIFIED RESOURCE LIBRARY below. Do NOT make up or hallucinate any other URLs, as they will break.

            === VERIFIED RESOURCE LIBRARY ===
            *Motivation & Study Habits (Exact Videos):*
            - Tim Urban: Inside the mind of a master procrastinator - https://www.youtube.com/watch?v=arj7oStGLkU
            - Angela Duckworth: Grit: the power of passion and perseverance - https://www.youtube.com/watch?v=H14bBuluwB8
            - Ali Abdaal: How to study for exams - Evidence-based revision tips - https://www.youtube.com/watch?v=ukLnPbIffxE
            - Matt D'Avella: How to stop procrastinating - https://www.youtube.com/watch?v=km4pOGd_lHw

            *Academic Channels:*
            - Khan Academy (Math/Science) - https://www.youtube.com/c/khanacademy
            - CrashCourse (General Topics) - https://www.youtube.com/user/crashcourse
            - MIT OpenCourseWare - https://www.youtube.com/c/mitocw
        """

        # 2. Fetch history
        history_rows = fetch_all("""
            SELECT sender_type, message_text 
            FROM chat_messages 
            WHERE session_id = :sid 
            ORDER BY message_id DESC 
            FETCH FIRST 5 ROWS ONLY
        """, {"sid": session_row["session_id"]})
        
        history_list = []
        for h in reversed(history_rows):
            history_list.append({
                "role": "user" if h["sender_type"] == "USER" else "assistant",
                "content": h["message_text"]
            })

    except Exception as e:
        print(f"Student context error: {str(e)}")
        system_prompt = f"You are ScholarAI Student Assistant for {name}."
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
        res = requests.post(
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

    return jsonify({'reply': reply})