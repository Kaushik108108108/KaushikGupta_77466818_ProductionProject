# This file handles all outgoing emails from the ScholarAI system.
# We use tools for sending messages and verifying that email addresses actually exist.
from flask_mail import Message
from .extensions import mail
import smtplib
import dns.resolver

# This function checks if an email address is real by talking to the recipient's mail server.
def verify_email_exists(email):
    # We first find the domain of the email (like gmail.com).
    domain = email.split('@')[1]
    try:
        # We look up the mail servers for that domain.
        records = dns.resolver.resolve(domain, 'MX')
        mx_record = str(sorted(records, key=lambda x: x.preference)[0].exchange)
        
        # We briefly connect to the mail server to ask if the specific email address is valid.
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_record)
        server.helo(server.local_hostname)
        server.mail('admin@scholarai.com')
        code, message = server.rcpt(str(email))
        server.quit()
        
        # If the server says 'OK' (code 250), the email is valid.
        if code == 250:
            return True, "Valid"
        else:
            return False, "This email account does not exist."
    except Exception:
        # If any step fails, we assume the email might be invalid.
        return False, "This email account does not exist."

# This is the main function for sending a custom message to anyone.
def send_custom_email(recipient, subject, body, cc=None):
    # Before sending, we check if the recipient's email is actually real.
    is_valid, msg = verify_email_exists(recipient)
    if not is_valid:
        return False, msg
        
    # If a CC was provided, we check that email address too.
    if cc:
        is_valid_cc, msg_cc = verify_email_exists(cc)
        if not is_valid_cc:
            return False, f"CC Email error: {msg_cc}"

    try:
        # We build the email message with the subject, body, and recipients.
        msg = Message(subject=subject, recipients=[recipient])
        if cc:
            msg.cc = [cc]
        msg.body = body
        # Finally, we send the email using our server settings.
        mail.send(msg)
        return True, "Email sent successfully."
    except Exception as e:
        # If something goes wrong during sending, we report the error.
        return False, str(e)

# This function sends a pre-written alert when a student is flagged as high-risk.
def send_high_risk_alert(student_name, recipient, cc=None):
    subject = f"URGENT: High Risk Academic Alert — {student_name}"
    body = (
        f"Dear {student_name} and Guardian,\n\n"
        "This student has been flagged HIGH RISK by ScholarAI. "
        "Immediate intervention is recommended.\n\n"
        "Best Regards,\n"
        "ScholarAI Admin"
    )
    return send_custom_email(recipient, subject, body, cc=cc)

# This function sends a secure link to users who need to reset their password.
def send_password_reset_email(recipient, reset_url):
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
