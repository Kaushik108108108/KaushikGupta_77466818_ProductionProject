from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, flash
from app.db import fetch_one, fetch_all, execute_dml

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


def _build_ai_recommendation(subject_name, predicted_score, attendance_rate, trend):
    notes = []

    if predicted_score < 55:
        notes.append(f'{subject_name}: urgent improvement needed. Revise weak chapters and ask for teacher support.')
    elif predicted_score < 75:
        notes.append(f'{subject_name}: average performance. Practice weekly and solve more sample questions.')
    else:
        notes.append(f'{subject_name}: good progress. Keep revising regularly to maintain your score.')

    if attendance_rate < 75:
        notes.append('Attendance is below the safe threshold. Attend every class and practical session.')
    elif attendance_rate < 85:
        notes.append('Attendance can be improved further for better consistency.')

    if trend == 'declining':
        notes.append('Your trend is declining. Review mistakes from earlier terms immediately.')
    elif trend == 'unstable':
        notes.append('Your results are inconsistent. Follow a fixed weekly study plan.')
    elif trend == 'improving':
        notes.append('Your trend is improving. Continue the same study routine.')

    return ' '.join(notes)


@student_bp.route('/dashboard')
@student_required
def dashboard():
    sid = session.get('student_id')
    student_info = _get_student_dashboard_info(sid)

    if not student_info:
        flash('Student profile not found.', 'error')
        return redirect(url_for('auth.student_logout'))

    recs = fetch_all("""
        SELECT
            NVL(sub.subject_name, 'General') AS subject_name,
            recommendation_text,
            rec_type
        FROM ai_recommendations ar
        LEFT JOIN subjects sub
          ON sub.subject_id = ar.subject_id
        WHERE ar.student_id = :sid
          AND ar.is_active = 'Y'
        ORDER BY ar.created_at DESC
    """, {"sid": sid})

    if not recs:
        recs = fetch_all("""
            SELECT
                sub.subject_name,
                NVL(ar.ai_recommendation, 'Keep practicing consistently and maintain regular attendance.') AS recommendation_text,
                CASE
                    WHEN NVL(ar.predicted_score, 0) < 55 THEN 'danger'
                    WHEN NVL(ar.predicted_score, 0) < 75 THEN 'warning'
                    ELSE 'success'
                END AS rec_type
            FROM student_academic_records ar
            JOIN subjects sub
              ON sub.subject_id = ar.subject_id
            WHERE ar.student_id = :sid
            ORDER BY sub.subject_name
        """, {"sid": sid})

    return render_template('student/dashboard.html', student=student_info, recs=recs)


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
            NVL(risk_level, 'low') AS risk_level
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

    score_avg = (term1_score + term2_score + term3_score) / 3
    att_factor = (attendance_rate / 100) * 25
    predicted_score = round((score_avg * 0.75) + att_factor)
    predicted_score = max(0, min(100, predicted_score))

    trend, trend_label, trend_note = calculate_trend(term1_score, term2_score, term3_score)

    if predicted_score >= 75:
        risk_level = 'low'
        pi_label = 'Excellent' if predicted_score >= 85 else 'Good'
    elif predicted_score >= 55:
        risk_level = 'medium'
        pi_label = 'Average'
    else:
        risk_level = 'high'
        pi_label = 'Below Average'

    if trend == 'declining' and risk_level == 'low':
        risk_level = 'medium'
    elif trend == 'declining' and risk_level == 'medium':
        risk_level = 'high'

    if attendance_rate < 65 and risk_level == 'low':
        risk_level = 'medium'
    elif attendance_rate < 65 and risk_level == 'medium':
        risk_level = 'high'

    grade = get_grade(predicted_score)
    prediction_id = _next_prediction_id()
    recommendation_text = _build_ai_recommendation(subject_name, predicted_score, attendance_rate, trend)

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
            0,
            0,
            :predicted_score,
            :risk_level,
            :trend,
            :trend_label,
            :trend_note,
            :grade,
            :performance_index_label,
            82,
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
        "predicted_score": predicted_score,
        "risk_level": risk_level,
        "trend": trend,
        "trend_label": trend_label,
        "trend_note": trend_note,
        "grade": grade,
        "performance_index_label": pi_label,
        "ai_recommendation": recommendation_text,
    })

    risk_flags = []
    if trend == 'declining':
        risk_flags.append('DECLINING TREND')
    if attendance_rate < 75:
        risk_flags.append('LOW ATTENDANCE')
    if predicted_score < 55:
        risk_flags.append('POOR ACADEMIC PERFORMANCE')

    for flag in risk_flags:
        execute_dml("""
            INSERT INTO prediction_flags (prediction_id, flag_name)
            VALUES (:prediction_id, :flag_name)
        """, {"prediction_id": prediction_id, "flag_name": flag})

    student_info = _get_student_dashboard_info(sid)
    recs = fetch_all("""
        SELECT
            NVL(sub.subject_name, 'General') AS subject_name,
            recommendation_text,
            rec_type
        FROM ai_recommendations ar
        LEFT JOIN subjects sub
          ON sub.subject_id = ar.subject_id
        WHERE ar.student_id = :sid
          AND ar.is_active = 'Y'
        ORDER BY ar.created_at DESC
    """, {"sid": sid})

    if not recs:
        recs = [
            {
                "subject_name": subject_name,
                "recommendation_text": recommendation_text,
                "rec_type": "danger" if risk_level == "high" else "warning" if risk_level == "medium" else "success",
            }
        ]

    result = {
        'predicted_score': predicted_score,
        'grade': grade,
        'pi_label': pi_label,
        'risk_level': risk_level,
        'confidence_score': 82,
        'trend': trend,
        'trend_label': trend_label,
        'trend_note': trend_note,
    }

    return render_template(
        'student/dashboard.html',
        student=student_info,
        recs=recs,
        result=result,
        subject_name=subject_name
    )


@student_bp.route('/activity')
@student_required
def activity():
    sid = session.get('student_id')

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
        ORDER BY created_at DESC
    """, {"sid": sid})

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
    best_subject = max(formatted_history, key=lambda p: float(p['predicted_score']))['subject_name'][:2].upper() if total else '--'

    stats = {
        'total': total,
        'high_risk': high_risk,
        'avg_score': avg_score,
        'best_subject': best_subject
    }

    return render_template('student/activity.html', history=formatted_history, stats=stats)


@student_bp.route('/chatbot')
@student_required
def chatbot():
    name = session.get('student_name', 'Student')
    sid = session.get('student_id', 'STU-001')

    chat_session = fetch_all("""
        SELECT
            session_id,
            session_label
        FROM chat_sessions
        WHERE owner_role = 'STUDENT'
          AND student_id = :sid
        ORDER BY created_at DESC
    """, {"sid": sid})

    return render_template(
        'student/chatbot.html',
        student_name=name,
        student_id=sid,
        chat_session=chat_session
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
    msg_lower = msg.lower()

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
                owner_role,
                admin_id,
                student_id,
                session_label,
                is_active
            )
            VALUES (
                'STUDENT',
                NULL,
                :student_id,
                :session_label,
                'Y'
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

    execute_dml("""
        INSERT INTO chat_messages (session_id, sender_type, message_text)
        VALUES (:session_id, 'USER', :message_text)
    """, {
        "session_id": session_row["session_id"],
        "message_text": msg
    })

    if 'science' in msg_lower or 'improve' in msg_lower:
        science_row = fetch_one("""
            SELECT
                NVL(p.subject_name_snapshot, s.subject_name) AS subject_name,
                NVL(p.predicted_score, ar.predicted_score) AS predicted_score,
                NVL(p.attendance_rate, ar.attendance_rate) AS attendance_rate,
                NVL(p.trend_label, ar.trend_label) AS trend_label
            FROM student_academic_records ar
            JOIN subjects s
              ON s.subject_id = ar.subject_id
            LEFT JOIN (
                SELECT p1.*
                FROM predictions p1
                WHERE p1.student_id = :sid
            ) p
              ON p.subject_id = ar.subject_id
            WHERE ar.student_id = :sid
              AND LOWER(s.subject_name) = 'science'
            FETCH FIRST 1 ROWS ONLY
        """, {"sid": sid})

        if science_row:
            reply = (
                f'Based on your {science_row["subject_name"]} records:\n'
                f'• Predicted score: {round(float(science_row["predicted_score"] or 0))}%\n'
                f'• Attendance rate: {round(float(science_row["attendance_rate"] or 0))}%\n'
                f'• Trend: {science_row["trend_label"] or "No trend yet"}\n\n'
                f'Recommendations:\n'
                f'1. Revise weak topics and solve past questions\n'
                f'2. Attend every class and practical session\n'
                f'3. Ask your teacher for a short review plan'
            )
        else:
            weakest = fetch_one("""
                SELECT
                    subject_name_snapshot AS subject_name,
                    predicted_score,
                    attendance_rate,
                    trend_label
                FROM predictions
                WHERE student_id = :sid
                ORDER BY predicted_score ASC, created_at DESC
                FETCH FIRST 1 ROWS ONLY
            """, {"sid": sid})

            if weakest:
                reply = (
                    f'Your weakest recent subject is {weakest["subject_name"]}.\n'
                    f'• Predicted score: {round(float(weakest["predicted_score"] or 0))}%\n'
                    f'• Attendance rate: {round(float(weakest["attendance_rate"] or 0))}%\n'
                    f'• Trend: {weakest["trend_label"] or "No trend yet"}\n\n'
                    f'Start by reviewing that subject for 30–45 minutes daily.'
                )
            else:
                reply = 'I need at least one prediction record before I can suggest improvement steps. Run a prediction first from your dashboard.'

    elif 'risk' in msg_lower:
        student_row = fetch_one("""
            SELECT
                NVL(risk_level, 'low') AS risk_level,
                NVL(performance_index, 0) AS performance_index
            FROM students
            WHERE student_id = :sid
        """, {"sid": sid})

        risky = fetch_all("""
            SELECT subject_name_snapshot AS subject_name, predicted_score
            FROM predictions
            WHERE student_id = :sid
              AND risk_level IN ('high', 'medium')
            ORDER BY predicted_score ASC, created_at DESC
            FETCH FIRST 3 ROWS ONLY
        """, {"sid": sid})

        if risky:
            risk_lines = '\n'.join(
                [f'⚠ {r["subject_name"]} — {round(float(r["predicted_score"]))}%'
                 for r in risky]
            )
        else:
            risk_lines = 'No high or medium-risk subject predictions found yet.'

        reply = (
            f'Hi {name}, your current overall risk level is {str(student_row["risk_level"]).upper()}.\n'
            f'Performance Index: {round(float(student_row["performance_index"]))}%\n\n'
            f'{risk_lines}'
        )

    elif 'trend' in msg_lower:
        rows = fetch_all("""
            SELECT
                subject_name_snapshot AS subject_name,
                trend_label
            FROM predictions
            WHERE student_id = :sid
            ORDER BY created_at DESC
        """, {"sid": sid})

        if rows:
            improving = [r["subject_name"] for r in rows if r["trend_label"] and "Improving" in r["trend_label"]]
            declining = [r["subject_name"] for r in rows if r["trend_label"] and "Declining" in r["trend_label"]]
            stable = [r["subject_name"] for r in rows if r["trend_label"] and "Stable" in r["trend_label"]]

            reply = (
                f'Your trend analysis:\n'
                f'↑ Improving: {", ".join(improving) if improving else "None"}\n'
                f'↓ Declining: {", ".join(declining) if declining else "None"}\n'
                f'→ Stable: {", ".join(stable) if stable else "None"}\n\n'
                f'Focus first on the declining subjects.'
            )
        else:
            reply = 'No trend data found yet. Run a prediction first so I can analyze your progress.'

    elif 'pi' in msg_lower or 'performance' in msg_lower:
        pi_row = fetch_one("""
            SELECT NVL(performance_index, 0) AS performance_index
            FROM students
            WHERE student_id = :sid
        """, {"sid": sid})

        reply = (
            f'Your Performance Index is stored from your student profile and academic records.\n'
            f'Your current PI: {round(float(pi_row["performance_index"]))}%\n\n'
            f'To improve it, raise subject scores and maintain strong attendance.'
        )

    else:
        reply = f'Let me check your academic profile for: "{msg}". Analyzing your records...'

    execute_dml("""
        INSERT INTO chat_messages (session_id, sender_type, message_text)
        VALUES (:session_id, 'BOT', :message_text)
    """, {
        "session_id": session_row["session_id"],
        "message_text": reply
    })

    return jsonify({'reply': reply})