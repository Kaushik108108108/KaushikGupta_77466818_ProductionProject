import os
import json
import urllib.request
import urllib.error


def generate_ai_recommendation(
    student_name: str,
    subject_name: str,
    risk_level: str,
    trend: str,
    predicted_score: float,
    attendance_rate: float,
    term1_score: float,
    term2_score: float,
    term3_score: float,
    complaint_count: int = 0,
    due_amount: float = 0,
    audience: str = "admin",   # "admin" or "student"
) -> str:
    """
    Call Anthropic claude-sonnet-4-20250514 to generate a personalised,
    subject-aware academic recommendation.

    Falls back to a rich rule-based recommendation if the API call fails
    so the rest of the app never breaks.
    """

    # ── Build a tight, structured prompt ──────────────────────────────
    tone = (
        "a school administrator reviewing student academic data"
        if audience == "admin"
        else "the student themselves who needs clear, motivating advice"
    )

    prompt = f"""You are an expert academic advisor writing for {tone}.

Student profile:
- Name          : {student_name}
- Subject       : {subject_name}
- Risk Level    : {risk_level.upper()}
- Performance Trend : {trend}
- Predicted Score   : {predicted_score:.1f}%
- Attendance Rate   : {attendance_rate:.1f}%
- Term 1 Score  : {term1_score}
- Term 2 Score  : {term2_score}
- Term 3 Score  : {term3_score}
- Complaint Count   : {complaint_count}
- Outstanding Dues  : Rs.{due_amount:,.0f}

Write a concise, specific academic recommendation (3–5 sentences) for this student in {subject_name}.
Focus on:
1. What the trend and scores reveal about their current trajectory
2. One or two concrete, actionable steps they or their teacher should take
3. If risk is high, include urgency; if low, include encouragement

Do NOT use bullet points. Write in flowing prose. Do NOT mention the student's name more than once.
Do NOT add any preamble like "Here is the recommendation:" — just write it directly."""

    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if api_key:
        try:
            payload = json.dumps({
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}]
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                text_blocks = [b["text"] for b in body.get("content", []) if b.get("type") == "text"]
                recommendation = " ".join(text_blocks).strip()
                if recommendation:
                    return recommendation

        except Exception:
            pass   # fall through to rule-based fallback

    # ── Rule-based fallback (always works, no API needed) ──────────────
    return _rule_based_recommendation(
        subject_name, risk_level, trend,
        predicted_score, attendance_rate,
        complaint_count, due_amount, audience
    )


def _rule_based_recommendation(
    subject_name, risk_level, trend,
    predicted_score, attendance_rate,
    complaint_count, due_amount, audience
) -> str:
    parts = []

    # ── Score context ──
    if predicted_score < 40:
        parts.append(
            f"The predicted score of {predicted_score:.0f}% in {subject_name} "
            f"indicates a critical academic gap that requires immediate intervention."
        )
    elif predicted_score < 55:
        parts.append(
            f"A predicted score of {predicted_score:.0f}% in {subject_name} "
            f"places this student well below the passing threshold."
        )
    elif predicted_score < 75:
        parts.append(
            f"The predicted score of {predicted_score:.0f}% in {subject_name} "
            f"is in the average range but leaves significant room for improvement."
        )
    else:
        parts.append(
            f"With a predicted score of {predicted_score:.0f}% in {subject_name}, "
            f"the student is performing strongly and should aim for distinction."
        )

    # ── Trend context ──
    if trend == "declining":
        parts.append(
            "The declining trend across all three terms is a serious concern — "
            "scores have dropped each term, suggesting increasing difficulty or disengagement."
        )
    elif trend == "improving":
        parts.append(
            "The consistently improving trend across terms is a very positive sign, "
            "showing dedication and effective study habits."
        )
    elif trend == "unstable":
        parts.append(
            "The unstable trend — rising then falling — suggests inconsistent effort "
            "or difficulty retaining knowledge between assessments."
        )
    elif trend == "recovering":
        parts.append(
            "Although Term 2 saw a dip, the recovery in Term 3 is encouraging "
            "and should be reinforced with continued support."
        )
    else:
        parts.append(
            "The stable trend shows consistent effort, though the current level "
            "needs to be raised to improve the overall outcome."
        )

    # ── Attendance ──
    if attendance_rate < 60:
        parts.append(
            f"Attendance at {attendance_rate:.0f}% is critically low — "
            "missed classes are directly contributing to poor academic performance."
        )
    elif attendance_rate < 75:
        parts.append(
            f"Attendance of {attendance_rate:.0f}% is below the required threshold; "
            "improving class presence will have an immediate positive impact."
        )

    # ── Action recommendation ──
    if risk_level == "high":
        if audience == "admin":
            parts.append(
                f"Arrange a parent meeting immediately, schedule weekly remedial sessions "
                f"in {subject_name}, and follow up every two weeks until scores improve."
            )
        else:
            parts.append(
                f"Attend every {subject_name} class without exception, seek help from "
                f"your teacher after school, and revise the weakest chapters daily."
            )
    elif risk_level == "medium":
        if audience == "admin":
            parts.append(
                f"Assign a study mentor for {subject_name} and monitor performance "
                f"fortnightly to prevent further decline into high-risk territory."
            )
        else:
            parts.append(
                f"Dedicate 30–45 minutes daily to {subject_name} revision, "
                f"focus on areas where term scores dropped, and complete all assignments on time."
            )
    else:
        if audience == "admin":
            parts.append(
                f"Continue recognising the student's progress in {subject_name} "
                f"and encourage participation in advanced or enrichment activities."
            )
        else:
            parts.append(
                f"Keep up your excellent work in {subject_name} — "
                f"maintain your study schedule and aim to push your score even higher next term."
            )

    # ── Financial note (admin only) ──
    if audience == "admin" and due_amount > 5000:
        parts.append(
            f"Outstanding dues of Rs.{due_amount:,.0f} should also be addressed "
            f"as financial stress may be affecting academic focus."
        )

    return " ".join(parts)