import json
from datetime import date
from pathlib import Path

import joblib
import pandas as pd

from app.db import execute_dml

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "scholarai_academic_score_pipeline.joblib"
META_PATH = ARTIFACT_DIR / "scholarai_model_metadata.json"
RULES_PATH = ARTIFACT_DIR / "scholarai_business_rules.json"

DEFAULT_RULES = {
    "risk_thresholds": {
        "low_min_score": 75,
        "medium_min_score": 55,
        "high_below_score": 55,
    },
    "recommendation_rules": {
        "attendance_lt_65": "Critical attendance: arrange immediate follow-up with guardian and class teacher.",
        "attendance_lt_75": "Low attendance: encourage consistent attendance and monitor weekly.",
        "predicted_score_lt_55": "Provide urgent academic intervention, remedial sessions, and progress tracking.",
        "predicted_score_lt_75": "Provide targeted support in weak areas and schedule additional practice.",
        "performance_unstable": "Performance is unstable across terms; review subject-level gaps and study plan.",
        "declining_trend": "Declining trend detected; plan early intervention before final assessment.",
    },
}

DEFAULT_METADATA = {
    "project": "ScholarAI",
    "purpose": "Predict academic score for Flask predicted_score column",
    "selected_model_name": "Formula fallback",
    "artifact_source": "formula_fallback",
    "website_features": [
        "attendance_rate",
        "term1_score",
        "term2_score",
        "term3_score",
        "terminal_avg",
    ],
    "final_metrics": {"display_confidence_pct": 78},
    "notes": [
        "A trained .joblib exported from the Colab notebook overrides the fallback formula automatically.",
    ],
}

_model = None
_metadata = None
_rules = None
_model_load_error = None


def _read_json(path: Path, default: dict):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return default


def _load_artifacts():
    global _model, _metadata, _rules, _model_load_error
    if _metadata is None:
        _metadata = _read_json(META_PATH, DEFAULT_METADATA.copy())
    if _rules is None:
        _rules = _read_json(RULES_PATH, DEFAULT_RULES.copy())
    if _model is None and MODEL_PATH.exists() and _model_load_error is None:
        try:
            _model = joblib.load(MODEL_PATH)
        except Exception as exc:
            _model_load_error = str(exc)
    return _model, _metadata, _rules


def get_model_metadata():
    _, metadata, _ = _load_artifacts()
    return metadata or DEFAULT_METADATA.copy()


def get_business_rules():
    _, _, rules = _load_artifacts()
    return rules or DEFAULT_RULES.copy()


def get_model_display_name():
    metadata = get_model_metadata()
    return (
        metadata.get("selected_model_name")
        or metadata.get("best_model_name")
        or metadata.get("model_name")
        or "Formula fallback"
    )


def get_model_confidence_pct(default: int = 82):
    metadata = get_model_metadata()
    metrics = metadata.get("final_metrics") or {}
    for key in ("display_confidence_pct", "confidence_pct", "test_r2", "r2"):
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            if key in {"test_r2", "r2"} and 0 <= value <= 1:
                return int(round(max(0, min(99, value * 100))))
            return int(round(max(0, min(99, value))))
    return int(default)


def _formula_fallback(attendance_rate, term1_score, term2_score, term3_score):
    score_avg = (term1_score + term2_score + term3_score) / 3
    att_factor = (attendance_rate / 100) * 25
    predicted_score = round((score_avg * 0.75) + att_factor, 2)
    return max(0.0, min(100.0, predicted_score))


def predict_score_bundle(attendance_rate, term1_score, term2_score, term3_score):
    model, metadata, _ = _load_artifacts()
    terminal_avg = round((term1_score + term2_score + term3_score) / 3, 2)
    input_df = pd.DataFrame([
        {
            "attendance_rate": attendance_rate,
            "term1_score": term1_score,
            "term2_score": term2_score,
            "term3_score": term3_score,
            "terminal_avg": terminal_avg,
        }
    ])

    source = "formula_fallback"
    predicted_score = _formula_fallback(attendance_rate, term1_score, term2_score, term3_score)
    if model is not None:
        try:
            predicted_score = float(model.predict(input_df)[0])
            predicted_score = round(max(0.0, min(100.0, predicted_score)), 2)
            source = metadata.get("artifact_source", "trained_model")
        except Exception:
            predicted_score = _formula_fallback(attendance_rate, term1_score, term2_score, term3_score)
            source = "formula_fallback"

    confidence_score = get_model_confidence_pct(78 if source == "formula_fallback" else 82)

    return {
        "predicted_score": predicted_score,
        "terminal_avg": terminal_avg,
        "confidence_score": confidence_score,
        "model_name": get_model_display_name(),
        "prediction_source": source,
        "website_features": metadata.get("website_features", DEFAULT_METADATA["website_features"]),
    }


def predict_academic_score(attendance_rate, term1_score, term2_score, term3_score):
    return predict_score_bundle(attendance_rate, term1_score, term2_score, term3_score)["predicted_score"]


def score_to_risk(score, rules=None):
    thresholds = (rules or get_business_rules()).get("risk_thresholds", {})
    low_min = float(thresholds.get("low_min_score", 75))
    medium_min = float(thresholds.get("medium_min_score", 55))
    if score >= low_min:
        return "low"
    if score >= medium_min:
        return "medium"
    return "high"


def calculate_trend(term1_score, term2_score, term3_score, audience="admin"):
    diff1 = term2_score - term1_score
    diff2 = term3_score - term2_score

    if audience == "student":
        if diff1 > 3 and diff2 > 3:
            return "improving", "↑ Improving", "You are consistently improving each term. Keep it up!"
        if diff1 < -3 and diff2 < -3:
            return "declining", "↓ Declining", "Your marks are dropping each term. Seek help immediately."
        if diff1 > 3 and diff2 < -3:
            return "unstable", "~ Unstable", "Marks went up then dropped. Try to maintain consistency."
        if diff1 < -3 and diff2 > 3:
            return "recovering", "↑ Recovering", "Marks dropped in term 2 but you recovered in term 3. Well done!"
        return "stable", "→ Stable", "Performance is consistent across all terms."

    if diff1 > 3 and diff2 > 3:
        return "improving", "↑ Improving", "Student is consistently improving each term."
    if diff1 < -3 and diff2 < -3:
        return "declining", "↓ Declining", "Student marks are dropping each term. Immediate attention needed."
    if diff1 > 3 and diff2 < -3:
        return "unstable", "~ Unstable", "Marks went up then dropped. Performance is inconsistent."
    if diff1 < -3 and diff2 > 3:
        return "recovering", "↑ Recovering", "Marks dropped in term 2 but recovered in term 3. Monitor closely."
    return "stable", "→ Stable", "Performance is consistent across all terms."


def calculate_final_risk(predicted_score, attendance_rate, complaint_count, due_amount, trend):
    rules = get_business_rules()
    base_risk = score_to_risk(predicted_score, rules=rules)
    risk_flags = []

    if complaint_count >= 3:
        risk_flags.append("HIGH BEHAVIOR RISK")
    elif complaint_count >= 1:
        risk_flags.append("BEHAVIOR WARNING")

    if due_amount > 5000:
        risk_flags.append("HIGH FINANCIAL RISK")
    elif due_amount > 0:
        risk_flags.append("FINANCIAL WARNING")

    if attendance_rate < 65:
        risk_flags.append("CRITICAL ATTENDANCE")
    elif attendance_rate < 75:
        risk_flags.append("LOW ATTENDANCE")

    if predicted_score < float(rules.get("risk_thresholds", {}).get("medium_min_score", 55)):
        risk_flags.append("POOR ACADEMIC PERFORMANCE")

    if trend == "declining":
        risk_flags.append("DECLINING TREND")
    elif trend == "unstable":
        risk_flags.append("UNSTABLE TREND")

    high_flags = {"HIGH BEHAVIOR RISK", "HIGH FINANCIAL RISK", "CRITICAL ATTENDANCE", "DECLINING TREND"}

    if base_risk == "low" and (len(risk_flags) >= 2 or any(flag in high_flags for flag in risk_flags)):
        final_risk = "medium"
    elif base_risk == "medium" and len(risk_flags) >= 1:
        final_risk = "high"
    else:
        final_risk = base_risk

    return final_risk, risk_flags


def get_grade(score):
    if score >= 85:
        return "A"
    if score >= 75:
        return "B+"
    if score >= 65:
        return "B"
    if score >= 55:
        return "C+"
    if score >= 45:
        return "C"
    return "F"


def get_pi_label(score):
    if score >= 85:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 55:
        return "Average"
    return "Below Average"


def build_prediction_payload(attendance_rate, term1_score, term2_score, term3_score, complaint_count=0, due_amount=0, audience="admin"):
    score_bundle = predict_score_bundle(attendance_rate, term1_score, term2_score, term3_score)
    trend, trend_label, trend_note = calculate_trend(term1_score, term2_score, term3_score, audience=audience)
    risk_level, risk_flags = calculate_final_risk(
        score_bundle["predicted_score"],
        attendance_rate,
        complaint_count,
        due_amount,
        trend,
    )
    return {
        **score_bundle,
        "trend": trend,
        "trend_label": trend_label,
        "trend_note": trend_note,
        "risk_level": risk_level,
        "risk_flags": risk_flags,
        "grade": get_grade(score_bundle["predicted_score"]),
        "pi_label": get_pi_label(score_bundle["predicted_score"]),
    }


def current_academic_year():
    return date.today().year


def upsert_student_academic_record(student_id, subject_id, attendance_rate, term1_score, term2_score, term3_score,
                                   predicted_score, grade, trend, trend_label, ai_recommendation, academic_year=None):
    academic_year = academic_year or current_academic_year()
    execute_dml(
        """
        MERGE INTO student_academic_records sar
        USING (
            SELECT :student_id AS student_id,
                   :subject_id AS subject_id,
                   :academic_year AS academic_year
            FROM dual
        ) src
        ON (
            sar.student_id = src.student_id
            AND sar.subject_id = src.subject_id
            AND sar.academic_year = src.academic_year
        )
        WHEN MATCHED THEN UPDATE SET
            sar.attendance_rate = :attendance_rate,
            sar.term1_score = :term1_score,
            sar.term2_score = :term2_score,
            sar.term3_score = :term3_score,
            sar.predicted_score = :predicted_score,
            sar.grade = :grade,
            sar.trend = :trend,
            sar.trend_label = :trend_label,
            sar.ai_recommendation = :ai_recommendation,
            sar.last_evaluated_at = CURRENT_TIMESTAMP,
            sar.updated_at = CURRENT_TIMESTAMP
        WHEN NOT MATCHED THEN INSERT (
            student_id, subject_id, academic_year, attendance_rate,
            term1_score, term2_score, term3_score, predicted_score,
            grade, trend, trend_label, ai_recommendation,
            last_evaluated_at, created_at, updated_at
        ) VALUES (
            :student_id, :subject_id, :academic_year, :attendance_rate,
            :term1_score, :term2_score, :term3_score, :predicted_score,
            :grade, :trend, :trend_label, :ai_recommendation,
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        """,
        {
            "student_id": student_id,
            "subject_id": subject_id,
            "academic_year": academic_year,
            "attendance_rate": attendance_rate,
            "term1_score": term1_score,
            "term2_score": term2_score,
            "term3_score": term3_score,
            "predicted_score": predicted_score,
            "grade": grade,
            "trend": trend,
            "trend_label": trend_label,
            "ai_recommendation": ai_recommendation,
        },
    )


def update_student_rollup(student_id, predicted_score, risk_level, attendance_rate, confidence_score,
                          trend=None, trend_label=None, trend_note=None):
    sql = """
        UPDATE students
        SET performance_index = :predicted_score,
            risk_level = :risk_level,
            attendance_rate = :attendance_rate,
            confidence_score = :confidence_score
    """
    params = {
        "predicted_score": predicted_score,
        "risk_level": risk_level,
        "attendance_rate": attendance_rate,
        "confidence_score": confidence_score,
        "student_id": student_id,
    }

    if trend is not None:
        sql += ", trend = :trend"
        params["trend"] = trend
    if trend_label is not None:
        sql += ", trend_label = :trend_label"
        params["trend_label"] = trend_label
    if trend_note is not None:
        sql += ", trend_note = :trend_note"
        params["trend_note"] = trend_note

    sql += " WHERE student_id = :student_id"
    execute_dml(sql, params)
