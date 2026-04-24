from flask_mail import Message
from .extensions import mail

def send_custom_email(recipient, subject, body, cc=None):
    """
    Sends a custom email with SMTP.
    """
    try:
        msg = Message(subject=subject, recipients=[recipient])
        if cc:
            msg.cc = [cc]
        msg.body = body
        mail.send(msg)
        return True, "Email sent successfully."
    except Exception as e:
        return False, str(e)

def send_high_risk_alert(student_name, recipient, cc=None):
    """
    Sends a high-risk alert email.
    """
    subject = f"URGENT: High Risk Academic Alert — {student_name}"
    body = (
        f"Dear {student_name} and Guardian,\n\n"
        "This student has been flagged HIGH RISK by ScholarAI. "
        "Immediate intervention is recommended.\n\n"
        "Best Regards,\n"
        "ScholarAI Admin"
    )
    return send_custom_email(recipient, subject, body, cc=cc)

def send_password_reset_email(recipient, reset_url):
    """
    Sends a password reset link to the user.
    """
    subject = "Reset Your ScholarAI Password"
    body = (
        "Hello,\n\n"
        "We received a request to reset your ScholarAI password. "
        "Click the link below to set a new password. This link will expire in 1 hour:\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, please ignore this email.\n\n"
        "Best Regards,\n"
        "ScholarAI Team"
    )
    return send_custom_email(recipient, subject, body)
