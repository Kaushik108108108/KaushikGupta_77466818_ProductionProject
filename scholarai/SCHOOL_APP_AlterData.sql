DELETE FROM prediction_flags;
DELETE FROM predictions;
DELETE FROM ai_recommendations;
DELETE FROM complaints;
DELETE FROM student_fee_dues;
DELETE FROM email_logs;
DELETE FROM student_academic_records;

COMMIT;

UPDATE students SET
    performance_index = 32,  attendance_rate = 42,  risk_level = 'high',
    due_amount = 18000, complaint_count = 5,
    confidence_score = 58,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Consistent drop across all terms.'
WHERE student_id = 'STU-001';

UPDATE students SET
    performance_index = 35,  attendance_rate = 45,  risk_level = 'high',
    due_amount = 16500, complaint_count = 4,
    confidence_score = 60,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Performance declining steadily.'
WHERE student_id = 'STU-002';

UPDATE students SET
    performance_index = 30,  attendance_rate = 40,  risk_level = 'high',
    due_amount = 20000, complaint_count = 5,
    confidence_score = 55,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Critical attendance and academic failure risk.'
WHERE student_id = 'STU-003';

UPDATE students SET
    performance_index = 38,  attendance_rate = 50,  risk_level = 'high',
    due_amount = 15000, complaint_count = 4,
    confidence_score = 60,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Weak performance across all subjects.'
WHERE student_id = 'STU-004';

UPDATE students SET
    performance_index = 33,  attendance_rate = 44,  risk_level = 'high',
    due_amount = 17000, complaint_count = 4,
    confidence_score = 57,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'High dues and disciplinary issues.'
WHERE student_id = 'STU-005';

UPDATE students SET
    performance_index = 36,  attendance_rate = 48,  risk_level = 'high',
    due_amount = 14000, complaint_count = 3,
    confidence_score = 62,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Needs immediate academic intervention.'
WHERE student_id = 'STU-006';

UPDATE students SET
    performance_index = 31,  attendance_rate = 41,  risk_level = 'high',
    due_amount = 19000, complaint_count = 5,
    confidence_score = 56,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Multiple risk flags: finance, attendance, academics.'
WHERE student_id = 'STU-007';

UPDATE students SET
    performance_index = 34,  attendance_rate = 46,  risk_level = 'high',
    due_amount = 13000, complaint_count = 3,
    confidence_score = 59,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Score dropped significantly in Term 3.'
WHERE student_id = 'STU-008';

UPDATE students SET
    performance_index = 37,  attendance_rate = 52,  risk_level = 'high',
    due_amount = 15500, complaint_count = 4,
    confidence_score = 61,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Persistent absenteeism and poor results.'
WHERE student_id = 'STU-009';

UPDATE students SET
    performance_index = 40,  attendance_rate = 55,  risk_level = 'high',
    due_amount = 12000, complaint_count = 3,
    confidence_score = 63,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Borderline high risk with unpaid dues.'
WHERE student_id = 'STU-010';

UPDATE students SET
    performance_index = 29,  attendance_rate = 40,  risk_level = 'high',
    due_amount = 20000, complaint_count = 5,
    confidence_score = 55,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Severe financial and academic crisis.'
WHERE student_id = 'STU-011';

UPDATE students SET
    performance_index = 32,  attendance_rate = 43,  risk_level = 'high',
    due_amount = 18500, complaint_count = 4,
    confidence_score = 57,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Low attendance and zero payment on dues.'
WHERE student_id = 'STU-012';

UPDATE students SET
    performance_index = 35,  attendance_rate = 47,  risk_level = 'high',
    due_amount = 16000, complaint_count = 4,
    confidence_score = 60,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Repeated disciplinary incidents.'
WHERE student_id = 'STU-013';

UPDATE students SET
    performance_index = 33,  attendance_rate = 45,  risk_level = 'high',
    due_amount = 17500, complaint_count = 3,
    confidence_score = 58,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Guardian not reachable; school flagged.'
WHERE student_id = 'STU-014';

UPDATE students SET
    performance_index = 38,  attendance_rate = 51,  risk_level = 'high',
    due_amount = 14500, complaint_count = 3,
    confidence_score = 62,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Declining trend in Math and Science.'
WHERE student_id = 'STU-015';

UPDATE students SET
    performance_index = 30,  attendance_rate = 42,  risk_level = 'high',
    due_amount = 19500, complaint_count = 5,
    confidence_score = 56,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'All three risk categories triggered.'
WHERE student_id = 'STU-016';

UPDATE students SET
    performance_index = 36,  attendance_rate = 49,  risk_level = 'high',
    due_amount = 13500, complaint_count = 3,
    confidence_score = 61,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Remedial classes attended but no improvement.'
WHERE student_id = 'STU-017';

UPDATE students SET
    performance_index = 34,  attendance_rate = 46,  risk_level = 'high',
    due_amount = 15000, complaint_count = 4,
    confidence_score = 59,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Parent notified; awaiting response.'
WHERE student_id = 'STU-018';

UPDATE students SET
    performance_index = 31,  attendance_rate = 43,  risk_level = 'high',
    due_amount = 18000, complaint_count = 4,
    confidence_score = 57,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Critical — intervention required.'
WHERE student_id = 'STU-019';

UPDATE students SET
    performance_index = 39,  attendance_rate = 53,  risk_level = 'high',
    due_amount = 12500, complaint_count = 3,
    confidence_score = 63,   trend = 'declining',
    trend_label = '↓ Declining', trend_note = 'Financial pressure affecting performance.'
WHERE student_id = 'STU-020';


-- ─────────────────────────────────────────
-- STEP 3 : MEDIUM RISK — STU-021 to STU-030
--   • scores 50–64
--   • attendance 65–74%
--   • complaint_count 1–2
--   • due_amount 3000–8000
--   • performance_index 52–64
--   • confidence_score 68–76
--   • trend = 'stable' or 'unstable'
-- ─────────────────────────────────────────

UPDATE students SET
    performance_index = 55,  attendance_rate = 68,  risk_level = 'medium',
    due_amount = 7500, complaint_count = 2,
    confidence_score = 70,   trend = 'stable',
    trend_label = '→ Stable', trend_note = 'Average performance with dues pending.'
WHERE student_id = 'STU-021';

UPDATE students SET
    performance_index = 58,  attendance_rate = 70,  risk_level = 'medium',
    due_amount = 6000, complaint_count = 1,
    confidence_score = 72,   trend = 'stable',
    trend_label = '→ Stable', trend_note = 'Moderate risk. Attendance borderline.'
WHERE student_id = 'STU-022';

UPDATE students SET
    performance_index = 52,  attendance_rate = 65,  risk_level = 'medium',
    due_amount = 8000, complaint_count = 2,
    confidence_score = 68,   trend = 'unstable',
    trend_label = '~ Unstable', trend_note = 'Scores fluctuating; dues unresolved.'
WHERE student_id = 'STU-023';

UPDATE students SET
    performance_index = 60,  attendance_rate = 72,  risk_level = 'medium',
    due_amount = 4500, complaint_count = 1,
    confidence_score = 74,   trend = 'stable',
    trend_label = '→ Stable', trend_note = 'Slightly below target; needs monitoring.'
WHERE student_id = 'STU-024';

UPDATE students SET
    performance_index = 54,  attendance_rate = 67,  risk_level = 'medium',
    due_amount = 7000, complaint_count = 2,
    confidence_score = 69,   trend = 'unstable',
    trend_label = '~ Unstable', trend_note = 'Inconsistent performance pattern.'
WHERE student_id = 'STU-025';

UPDATE students SET
    performance_index = 62,  attendance_rate = 73,  risk_level = 'medium',
    due_amount = 3500, complaint_count = 1,
    confidence_score = 75,   trend = 'stable',
    trend_label = '→ Stable', trend_note = 'Close to low risk; minor dues.'
WHERE student_id = 'STU-026';

UPDATE students SET
    performance_index = 56,  attendance_rate = 69,  risk_level = 'medium',
    due_amount = 5500, complaint_count = 2,
    confidence_score = 71,   trend = 'unstable',
    trend_label = '~ Unstable', trend_note = 'Attendance and scores both need work.'
WHERE student_id = 'STU-027';

UPDATE students SET
    performance_index = 63,  attendance_rate = 74,  risk_level = 'medium',
    due_amount = 3000, complaint_count = 1,
    confidence_score = 76,   trend = 'stable',
    trend_label = '→ Stable', trend_note = 'Borderline medium; small dues remaining.'
WHERE student_id = 'STU-028';

UPDATE students SET
    performance_index = 53,  attendance_rate = 66,  risk_level = 'medium',
    due_amount = 6500, complaint_count = 2,
    confidence_score = 68,   trend = 'unstable',
    trend_label = '~ Unstable', trend_note = 'Two behavioral complaints on record.'
WHERE student_id = 'STU-029';

UPDATE students SET
    performance_index = 61,  attendance_rate = 71,  risk_level = 'medium',
    due_amount = 4000, complaint_count = 1,
    confidence_score = 73,   trend = 'stable',
    trend_label = '→ Stable', trend_note = 'Moderate performance; dues partially paid.'
WHERE student_id = 'STU-030';


-- ─────────────────────────────────────────
-- STEP 4 : LOW RISK — STU-031 to STU-060
--   • scores 75–95
--   • attendance 80–99%
--   • complaint_count 0
--   • due_amount 0   ← ZERO dues as required
--   • performance_index 72–95
--   • confidence_score 80–95
--   • trend = 'stable' or 'improving'
-- ─────────────────────────────────────────

UPDATE students SET performance_index=75,  attendance_rate=85, risk_level='low', due_amount=0, complaint_count=0, confidence_score=82, trend='stable',    trend_label='→ Stable',    trend_note='Good standing, consistent results.' WHERE student_id='STU-031';
UPDATE students SET performance_index=80,  attendance_rate=88, risk_level='low', due_amount=0, complaint_count=0, confidence_score=84, trend='improving',  trend_label='↑ Improving', trend_note='Scores improving each term.'         WHERE student_id='STU-032';
UPDATE students SET performance_index=78,  attendance_rate=86, risk_level='low', due_amount=0, complaint_count=0, confidence_score=83, trend='stable',    trend_label='→ Stable',    trend_note='Excellent attendance, clear dues.'   WHERE student_id='STU-033';
UPDATE students SET performance_index=85,  attendance_rate=91, risk_level='low', due_amount=0, complaint_count=0, confidence_score=88, trend='improving',  trend_label='↑ Improving', trend_note='Consistent top performer.'            WHERE student_id='STU-034';
UPDATE students SET performance_index=72,  attendance_rate=80, risk_level='low', due_amount=0, complaint_count=0, confidence_score=80, trend='stable',    trend_label='→ Stable',    trend_note='Meeting all academic targets.'       WHERE student_id='STU-035';
UPDATE students SET performance_index=88,  attendance_rate=93, risk_level='low', due_amount=0, complaint_count=0, confidence_score=90, trend='improving',  trend_label='↑ Improving', trend_note='Top scorer in section.'              WHERE student_id='STU-036';
UPDATE students SET performance_index=76,  attendance_rate=83, risk_level='low', due_amount=0, complaint_count=0, confidence_score=81, trend='stable',    trend_label='→ Stable',    trend_note='No issues; clean record.'           WHERE student_id='STU-037';
UPDATE students SET performance_index=82,  attendance_rate=89, risk_level='low', due_amount=0, complaint_count=0, confidence_score=86, trend='improving',  trend_label='↑ Improving', trend_note='Steady improvement in all subjects.' WHERE student_id='STU-038';
UPDATE students SET performance_index=79,  attendance_rate=87, risk_level='low', due_amount=0, complaint_count=0, confidence_score=84, trend='stable',    trend_label='→ Stable',    trend_note='Healthy academic profile.'          WHERE student_id='STU-039';
UPDATE students SET performance_index=91,  attendance_rate=96, risk_level='low', due_amount=0, complaint_count=0, confidence_score=93, trend='improving',  trend_label='↑ Improving', trend_note='Exceptional student, model profile.' WHERE student_id='STU-040';
UPDATE students SET performance_index=74,  attendance_rate=82, risk_level='low', due_amount=0, complaint_count=0, confidence_score=81, trend='stable',    trend_label='→ Stable',    trend_note='Passing all subjects comfortably.'  WHERE student_id='STU-041';
UPDATE students SET performance_index=86,  attendance_rate=92, risk_level='low', due_amount=0, complaint_count=0, confidence_score=89, trend='improving',  trend_label='↑ Improving', trend_note='Rising performance in Science.'      WHERE student_id='STU-042';
UPDATE students SET performance_index=77,  attendance_rate=84, risk_level='low', due_amount=0, complaint_count=0, confidence_score=82, trend='stable',    trend_label='→ Stable',    trend_note='Reliable attendance, zero dues.'    WHERE student_id='STU-043';
UPDATE students SET performance_index=83,  attendance_rate=90, risk_level='low', due_amount=0, complaint_count=0, confidence_score=87, trend='improving',  trend_label='↑ Improving', trend_note='Strong and improving performance.'   WHERE student_id='STU-044';
UPDATE students SET performance_index=73,  attendance_rate=81, risk_level='low', due_amount=0, complaint_count=0, confidence_score=80, trend='stable',    trend_label='→ Stable',    trend_note='Minimal risk, all dues clear.'      WHERE student_id='STU-045';
UPDATE students SET performance_index=89,  attendance_rate=94, risk_level='low', due_amount=0, complaint_count=0, confidence_score=91, trend='improving',  trend_label='↑ Improving', trend_note='Consistently high scores.'           WHERE student_id='STU-046';
UPDATE students SET performance_index=75,  attendance_rate=83, risk_level='low', due_amount=0, complaint_count=0, confidence_score=81, trend='stable',    trend_label='→ Stable',    trend_note='Good discipline and results.'       WHERE student_id='STU-047';
UPDATE students SET performance_index=81,  attendance_rate=88, risk_level='low', due_amount=0, complaint_count=0, confidence_score=85, trend='improving',  trend_label='↑ Improving', trend_note='Improved since last semester.'       WHERE student_id='STU-048';
UPDATE students SET performance_index=78,  attendance_rate=86, risk_level='low', due_amount=0, complaint_count=0, confidence_score=83, trend='stable',    trend_label='→ Stable',    trend_note='All academic obligations met.'      WHERE student_id='STU-049';
UPDATE students SET performance_index=93,  attendance_rate=98, risk_level='low', due_amount=0, complaint_count=0, confidence_score=95, trend='improving',  trend_label='↑ Improving', trend_note='School topper. No issues at all.'   WHERE student_id='STU-050';
UPDATE students SET performance_index=74,  attendance_rate=82, risk_level='low', due_amount=0, complaint_count=0, confidence_score=80, trend='stable',    trend_label='→ Stable',    trend_note='Stable and consistent learner.'     WHERE student_id='STU-051';
UPDATE students SET performance_index=87,  attendance_rate=93, risk_level='low', due_amount=0, complaint_count=0, confidence_score=90, trend='improving',  trend_label='↑ Improving', trend_note='Class participation is excellent.'  WHERE student_id='STU-052';
UPDATE students SET performance_index=76,  attendance_rate=84, risk_level='low', due_amount=0, complaint_count=0, confidence_score=82, trend='stable',    trend_label='→ Stable',    trend_note='Compliant with all school norms.'   WHERE student_id='STU-053';
UPDATE students SET performance_index=84,  attendance_rate=91, risk_level='low', due_amount=0, complaint_count=0, confidence_score=88, trend='improving',  trend_label='↑ Improving', trend_note='Term 3 score highest so far.'       WHERE student_id='STU-054';
UPDATE students SET performance_index=72,  attendance_rate=80, risk_level='low', due_amount=0, complaint_count=0, confidence_score=80, trend='stable',    trend_label='→ Stable',    trend_note='No complaints, dues, or issues.'    WHERE student_id='STU-055';
UPDATE students SET performance_index=90,  attendance_rate=95, risk_level='low', due_amount=0, complaint_count=0, confidence_score=92, trend='improving',  trend_label='↑ Improving', trend_note='Outstanding academic performance.'  WHERE student_id='STU-056';
UPDATE students SET performance_index=77,  attendance_rate=85, risk_level='low', due_amount=0, complaint_count=0, confidence_score=82, trend='stable',    trend_label='→ Stable',    trend_note='Steady progress every term.'        WHERE student_id='STU-057';
UPDATE students SET performance_index=83,  attendance_rate=90, risk_level='low', due_amount=0, complaint_count=0, confidence_score=86, trend='improving',  trend_label='↑ Improving', trend_note='Subject-wise improvement noted.'    WHERE student_id='STU-058';
UPDATE students SET performance_index=79,  attendance_rate=87, risk_level='low', due_amount=0, complaint_count=0, confidence_score=84, trend='stable',    trend_label='→ Stable',    trend_note='Good standing across all terms.'   WHERE student_id='STU-059';
UPDATE students SET performance_index=92,  attendance_rate=97, risk_level='low', due_amount=0, complaint_count=0, confidence_score=94, trend='improving',  trend_label='↑ Improving', trend_note='Leadership student, top of class.'  WHERE student_id='STU-060';

COMMIT;


-- ─────────────────────────────────────────
-- STEP 5 : ACADEMIC RECORDS
--   HIGH  : term scores 25–48, attendance 40–62
--   MEDIUM: term scores 50–64, attendance 65–74
--   LOW   : term scores 75–95, attendance 80–99
-- ─────────────────────────────────────────

INSERT INTO student_academic_records (
    student_id, subject_id, academic_year, attendance_rate,
    term1_score, term2_score, term3_score,
    predicted_score, grade, trend, trend_label, ai_recommendation, last_evaluated_at
)
SELECT
    s.student_id,
    sub.subject_id,
    2026,
    -- Attendance tied to student risk profile
    CASE s.risk_level
        WHEN 'high'   THEN GREATEST(40, LEAST(62, s.attendance_rate + MOD(sub.subject_id, 5) - 2))
        WHEN 'medium' THEN GREATEST(65, LEAST(74, s.attendance_rate + MOD(sub.subject_id, 3) - 1))
        ELSE               GREATEST(80, LEAST(99, s.attendance_rate + MOD(sub.subject_id, 4) - 1))
    END AS attendance_rate,
    -- Term 1
    CASE s.risk_level
        WHEN 'high'   THEN 25 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 20)
        WHEN 'medium' THEN 50 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 14)
        ELSE               75 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 18)
    END AS term1_score,
    -- Term 2
    CASE s.risk_level
        WHEN 'high'   THEN 22 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 2 + sub.subject_id * 3, 22)
        WHEN 'medium' THEN 48 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 2 + sub.subject_id * 3, 16)
        ELSE               73 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 2 + sub.subject_id * 3, 20)
    END AS term2_score,
    -- Term 3 (declining for high, stable for medium, improving for low)
    CASE s.risk_level
        WHEN 'high'   THEN 20 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 3 + sub.subject_id * 4, 20)
        WHEN 'medium' THEN 50 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 3 + sub.subject_id * 4, 14)
        ELSE               78 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 3 + sub.subject_id * 4, 17)
    END AS term3_score,
    -- Predicted
    CASE s.risk_level
        WHEN 'high'   THEN ROUND((
            (25 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 20)) +
            (22 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 2 + sub.subject_id * 3, 22)) +
            (20 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 3 + sub.subject_id * 4, 20))
        ) / 3, 2)
        WHEN 'medium' THEN ROUND((
            (50 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 14)) +
            (48 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 2 + sub.subject_id * 3, 16)) +
            (50 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 3 + sub.subject_id * 4, 14))
        ) / 3, 2)
        ELSE ROUND((
            (75 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 18)) +
            (73 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 2 + sub.subject_id * 3, 20)) +
            (78 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) * 3 + sub.subject_id * 4, 17))
        ) / 3, 2)
    END AS predicted_score,
    -- Grade
    CASE s.risk_level
        WHEN 'high'   THEN 'D'
        WHEN 'medium' THEN 'C'
        ELSE 'B'
    END AS grade,
    -- Trend
    CASE s.risk_level
        WHEN 'high'   THEN 'declining'
        WHEN 'medium' THEN 'stable'
        ELSE 'improving'
    END AS trend,
    -- Trend label
    CASE s.risk_level
        WHEN 'high'   THEN 'Declining'
        WHEN 'medium' THEN 'Stable'
        ELSE 'Improving'
    END AS trend_label,
    -- Recommendation
    CASE s.risk_level
        WHEN 'high'   THEN 'Urgent remedial support required. Daily follow-up and parent communication needed.'
        WHEN 'medium' THEN 'Monitor weekly. Increase revision frequency and complete pending assignments.'
        ELSE 'Keep up the excellent work. Maintain attendance and target distinction marks.'
    END AS ai_recommendation,
    CURRENT_TIMESTAMP
FROM students s
CROSS JOIN subjects sub;

COMMIT;


-- ─────────────────────────────────────────
-- STEP 6 : FEE DUES
--   HIGH   : OVERDUE, large amounts, partial/no payment
--   MEDIUM : PENDING, moderate amounts, no payment
--   LOW    : No records (due_amount = 0)
-- ─────────────────────────────────────────

-- HIGH RISK — Term 1 Tuition (OVERDUE)
INSERT INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
SELECT s.student_id, '2026 Term 1', 'Tuition Fee', s.due_amount, ROUND(s.due_amount * 0.15),
       DATE '2026-01-15', 'OVERDUE', 'High risk student — immediate payment required'
FROM students s WHERE s.risk_level = 'high';

-- HIGH RISK — Term 2 Examination Fee
INSERT INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
SELECT s.student_id, '2026 Term 2', 'Examination Fee', 2500, 0,
       DATE '2026-03-01', 'OVERDUE', 'Exam fee unpaid — student flagged'
FROM students s WHERE s.risk_level = 'high';

-- HIGH RISK — Sports/Activity Fee
INSERT INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
SELECT s.student_id, '2026 Term 1', 'Activity Fund', 1500, 0,
       DATE '2026-02-15', 'OVERDUE', 'Activity dues overdue'
FROM students s WHERE s.risk_level = 'high';

-- MEDIUM RISK — Term 1 Tuition (PENDING)
INSERT INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
SELECT s.student_id, '2026 Term 1', 'Tuition Fee', s.due_amount, 0,
       DATE '2026-04-15', 'PENDING', 'Medium risk student — payment pending'
FROM students s WHERE s.risk_level = 'medium';

-- MEDIUM RISK — Library Fee (PENDING)
INSERT INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
SELECT s.student_id, '2026 Term 1', 'Library Fee', 800, 0,
       DATE '2026-04-30', 'PENDING', 'Library dues pending'
FROM students s WHERE s.risk_level = 'medium';

COMMIT;


-- ─────────────────────────────────────────
-- STEP 7 : COMPLAINTS
--   HIGH   : 3–5 complaints (DISCIPLINARY, ATTENDANCE, ACADEMIC, FINANCE, OTHER)
--   MEDIUM : 1–2 complaints (ATTENDANCE or ACADEMIC)
--   LOW    : 0 complaints
-- ─────────────────────────────────────────

-- HIGH RISK complaints (5 per student)
INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'DISCIPLINARY',
       'Student repeatedly disrupts class. Warned three times this semester.',
       'HIGH', 'OPEN',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(30, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'high';

INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'ATTENDANCE',
       'Student absent for more than 40% of classes. Guardian notified.',
       'HIGH', 'OPEN',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(25, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'high';

INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'ACADEMIC',
       'Student failed two consecutive term assessments. Needs immediate academic support.',
       'HIGH', 'UNDER_REVIEW',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(20, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'high';

INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'FINANCE',
       'Outstanding fee dues not settled despite repeated reminders.',
       'HIGH', 'OPEN',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(15, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'high';

INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'OTHER',
       'Student involved in misconduct incident outside classroom.',
       'MEDIUM', 'OPEN',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(10, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'high';

-- MEDIUM RISK complaints (2 per student — ATTENDANCE + ACADEMIC)
INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'ATTENDANCE',
       'Attendance has dropped below the 75% threshold. Monitoring required.',
       'MEDIUM', 'OPEN',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(18, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'medium';

INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT s.student_id, 'ACADEMIC',
       'Performance is below class average. Extra coaching recommended.',
       'LOW', 'UNDER_REVIEW',
       CURRENT_TIMESTAMP - NUMTODSINTERVAL(12, 'DAY'), 'ADM-001'
FROM students s WHERE s.risk_level = 'medium';

-- Sync complaint_count from actual complaint table
UPDATE students s SET complaint_count = (
    SELECT COUNT(*) FROM complaints c WHERE c.student_id = s.student_id
);

COMMIT;


-- ─────────────────────────────────────────
-- STEP 8 : AI RECOMMENDATIONS
-- ─────────────────────────────────────────

INSERT INTO ai_recommendations (student_id, subject_id, recommendation_text, rec_type, source_type, is_active)
SELECT
    s.student_id,
    sub.subject_id,
    CASE s.risk_level
        WHEN 'high'   THEN 'Immediate intervention required. Schedule parent meeting, arrange remedial classes, and monitor weekly.'
        WHEN 'medium' THEN 'Increase study hours and complete all assignments. Monitor attendance and settle dues promptly.'
        ELSE 'Maintain current study habits and keep attendance above 85%. Target distinction grade.'
    END,
    CASE s.risk_level WHEN 'high' THEN 'danger' WHEN 'medium' THEN 'warning' ELSE 'success' END,
    'SYSTEM', 'Y'
FROM students s
JOIN subjects sub ON sub.subject_code = 'MATH';

COMMIT;


-- ─────────────────────────────────────────
-- STEP 9 : PREDICTIONS SEED (for training data)
-- ─────────────────────────────────────────

INSERT INTO predictions (
    prediction_id, student_id, subject_id,
    subject_name_snapshot, full_name_snapshot, class_level_snapshot,
    term1_score, term2_score, term3_score, attendance_rate,
    complaint_count_snapshot, due_amount_snapshot,
    predicted_score, risk_level, trend, trend_label, trend_note,
    grade, performance_index_label, confidence_score,
    ai_recommendation, predicted_by_role, predicted_by_admin_id, created_at
)
SELECT
    'PRD-' || LPAD(ROW_NUMBER() OVER (ORDER BY s.student_id, ar.subject_id), 4, '0'),
    s.student_id,
    ar.subject_id,
    sub.subject_name,
    s.full_name,
    s.class_level,
    ar.term1_score,
    ar.term2_score,
    ar.term3_score,
    ar.attendance_rate,
    s.complaint_count,
    s.due_amount,
    ar.predicted_score,
    s.risk_level,
    ar.trend,
    ar.trend_label,
    CASE ar.trend
        WHEN 'declining' THEN 'Performance dropping. Immediate action needed.'
        WHEN 'improving' THEN 'Positive trajectory. Keep up the effort.'
        ELSE 'Consistent performance. Maintain current pace.'
    END,
    ar.grade,
    CASE s.risk_level WHEN 'high' THEN 'Poor' WHEN 'medium' THEN 'Average' ELSE 'Good' END,
    s.confidence_score,
    ar.ai_recommendation,
    'System',
    NULL,
    CURRENT_TIMESTAMP - NUMTODSINTERVAL(TO_NUMBER(SUBSTR(s.student_id, 5)), 'MINUTE')
FROM students s
JOIN student_academic_records ar ON ar.student_id = s.student_id
JOIN subjects sub ON sub.subject_id = ar.subject_id
WHERE sub.subject_code = 'MATH';

COMMIT;


-- ─────────────────────────────────────────
-- STEP 10 : PREDICTION FLAGS
-- ─────────────────────────────────────────

INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT prediction_id, 'POOR ACADEMIC PERFORMANCE'
FROM predictions WHERE predicted_score < 50;

INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT prediction_id, 'DECLINING TREND'
FROM predictions WHERE trend = 'declining';

INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT prediction_id, 'HIGH BEHAVIOR RISK'
FROM predictions WHERE complaint_count_snapshot >= 3;

INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT prediction_id, 'HIGH FINANCIAL RISK'
FROM predictions WHERE due_amount_snapshot >= 10000;

INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT prediction_id, 'CRITICAL ATTENDANCE'
FROM predictions WHERE attendance_rate < 60;

COMMIT;