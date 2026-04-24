-- 1. CLEANUP (Idempotency)
DELETE FROM prediction_flags WHERE prediction_id IN (SELECT prediction_id FROM predictions WHERE student_id BETWEEN 'STU-061' AND 'STU-090');
DELETE FROM predictions WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
DELETE FROM ai_recommendations WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
DELETE FROM complaints WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
DELETE FROM student_fee_dues WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
DELETE FROM student_academic_records WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
-- 2. ACADEMIC RECORDS (7 subjects per student)
INSERT INTO student_academic_records (student_id, subject_id, academic_year, attendance_rate, term1_score, term2_score, term3_score, predicted_score, grade, trend, trend_label, ai_recommendation, last_evaluated_at)
SELECT 
    s.student_id, 
    sub.subject_id, 
    2026,
    s.attendance_rate + (MOD(sub.subject_id, 5) - 2), -- Slight variation per subject
    50 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id, 10),
    48 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 2, 12),
    45 + MOD(TO_NUMBER(SUBSTR(s.student_id, 5)) + sub.subject_id * 3, 15),
    s.performance_index,
    'C',
    s.trend,
    s.trend_label,
    'Focus on improving ' || sub.subject_name || ' by attending extra help sessions. Your ' || s.trend || ' trend needs monitoring.',
    CURRENT_TIMESTAMP
FROM students s
CROSS JOIN subjects sub
WHERE s.student_id BETWEEN 'STU-061' AND 'STU-090';
-- 3. FEE DUES (2 records per student)
INSERT ALL
    INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
    VALUES (sid, '2026 Term 1', 'Tuition Fee', dues, 0, DATE '2026-05-15', 'PENDING', 'Second installment pending.')
    INTO student_fee_dues (student_id, term_label, due_title, amount_due, amount_paid, due_date, status, notes)
    VALUES (sid, '2026 Term 1', 'Library & Lab Fee', 1200, 0, DATE '2026-05-20', 'PENDING', 'Standard laboratory dues.')
SELECT student_id as sid, due_amount as dues FROM students WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
-- 4. COMPLAINTS (Based on student.complaint_count)
INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT 
    s.student_id,
    CASE WHEN MOD(TO_NUMBER(SUBSTR(s.student_id, 5)), 2) = 0 THEN 'ATTENDANCE' ELSE 'ACADEMIC' END,
    'System generated flag: Performance/Attendance below threshold for medium risk profile.',
    'MEDIUM',
    'OPEN',
    CURRENT_TIMESTAMP - INTERVAL '10' DAY,
    'ADM-001'
FROM students s
WHERE s.student_id BETWEEN 'STU-061' AND 'STU-090';
-- Add a second complaint for those with count = 2
INSERT INTO complaints (student_id, complaint_type, description, severity, status, recorded_at, recorded_by_admin_id)
SELECT 
    s.student_id,
    'OTHER',
    'Follow up required regarding consistent late arrivals to morning assembly.',
    'LOW',
    'OPEN',
    CURRENT_TIMESTAMP - INTERVAL '5' DAY,
    'ADM-001'
FROM students s
WHERE s.student_id BETWEEN 'STU-061' AND 'STU-090' AND s.complaint_count >= 2;
-- 5. PREDICTIONS (Snapshot for Mathematics)
INSERT INTO predictions (
    prediction_id, student_id, subject_id, subject_name_snapshot, full_name_snapshot, class_level_snapshot,
    term1_score, term2_score, term3_score, attendance_rate, complaint_count_snapshot, due_amount_snapshot,
    predicted_score, risk_level, trend, trend_label, trend_note, grade, performance_index_label, confidence_score,
    ai_recommendation, predicted_by_role, created_at
)
SELECT 
    'PRD-M' || SUBSTR(s.student_id, 5),
    s.student_id,
    sub.subject_id,
    sub.subject_name,
    s.full_name,
    s.class_level,
    sar.term1_score,
    sar.term2_score,
    sar.term3_score,
    s.attendance_rate,
    s.complaint_count,
    s.due_amount,
    s.performance_index,
    'medium',
    s.trend,
    s.trend_label,
    s.trend_note,
    'C',
    'Average',
    s.confidence_score,
    'Academic intervention recommended for ' || sub.subject_name || '.',
    'System',
    CURRENT_TIMESTAMP
FROM students s
JOIN subjects sub ON sub.subject_code = 'MATH'
JOIN student_academic_records sar ON sar.student_id = s.student_id AND sar.subject_id = sub.subject_id
WHERE s.student_id BETWEEN 'STU-061' AND 'STU-090';
-- 6. PREDICTION FLAGS
INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT 'PRD-M' || SUBSTR(student_id, 5), 'BORDERLINE PERFORMANCE' FROM students WHERE student_id BETWEEN 'STU-061' AND 'STU-090';
INSERT INTO prediction_flags (prediction_id, flag_name)
SELECT 'PRD-M' || SUBSTR(student_id, 5), 'PENDING DUES' FROM students WHERE student_id BETWEEN 'STU-061' AND 'STU-090' AND due_amount > 0;
-- 7. AI RECOMMENDATIONS
INSERT INTO ai_recommendations (student_id, subject_id, recommendation_text, rec_type, source_type, is_active, created_at)
SELECT 
    s.student_id,
    sub.subject_id,
    'Based on your ' || s.trend || ' trend in ' || sub.subject_name || ', we recommend 2 hours of extra practice per week.',
    'warning',
    'MODEL',
    'Y',
    CURRENT_TIMESTAMP
FROM students s
JOIN subjects sub ON sub.subject_code = 'MATH'
WHERE s.student_id BETWEEN 'STU-061' AND 'STU-090';
COMMIT;