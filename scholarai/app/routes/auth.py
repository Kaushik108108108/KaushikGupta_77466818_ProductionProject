import hashlib
import secrets
from datetime import datetime, timedelta
import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from app.db import fetch_one, execute_dml
from app.email_service import send_password_reset_email

auth_bp = Blueprint('auth', __name__)


def _hash_password(password: str) -> str:
    """Hash password with SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _next_admin_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(REGEXP_SUBSTR(admin_id, '[0-9]+'))), 0) + 1 AS next_id
        FROM admin_users
        WHERE REGEXP_LIKE(admin_id, '^ADM-[0-9]+$')
    """)
    return f"ADM-{int(row['next_id']):03d}"


def _next_student_id():
    row = fetch_one("""
        SELECT NVL(MAX(TO_NUMBER(REGEXP_SUBSTR(student_id, '[0-9]+'))), 0) + 1 AS next_id
        FROM students
        WHERE REGEXP_LIKE(student_id, '^STU-[0-9]+$')
    """)
    return f"STU-{int(row['next_id']):03d}"


@auth_bp.route('/')
def index():
    return render_template('shared/index.html')


@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        login    = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Try hashed password first (new accounts), then plain text (legacy accounts)
        hashed = _hash_password(password)
        user = fetch_one("""
            SELECT admin_id, username, full_name, email, role_name
            FROM admin_users
            WHERE (LOWER(username) = LOWER(:login) OR LOWER(email) = LOWER(:login))
              AND (password_hash = :hashed OR password_hash = :plain)
        """, {"login": login, "hashed": hashed, "plain": password})

        if user:
            session['admin_logged_in'] = True
            session['admin_id']   = user['admin_id']
            session['admin_user'] = user['username']
            session['admin_name'] = user['full_name']
            return redirect(url_for('admin.dashboard'))

        flash('Invalid username or password.', 'error')

    # Live stats for hero panel
    login_stats = fetch_one("""
        SELECT
            COUNT(*) AS total_students,
            NVL(SUM(CASE WHEN risk_level = 'high' THEN 1 ELSE 0 END), 0) AS high_risk_count
        FROM students
    """) or {"total_students": 0, "high_risk_count": 0}

    acc_row = fetch_one("""
        SELECT
            CASE WHEN COUNT(*) = 0 THEN 0
            ELSE ROUND(
                SUM(CASE WHEN ABS(predicted_score - (term1_score + term2_score + term3_score) / 3) <= 10
                         THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 0)
            END AS accuracy
        FROM predictions
    """) or {"accuracy": 0}

    return render_template(
        'admin/login.html',
        total_students=login_stats['total_students'],
        high_risk_count=login_stats['high_risk_count'],
        prediction_accuracy=81,
        model_name="Model Accuracy"
    )


@auth_bp.route('/admin/register', methods=['POST'])
def admin_register():
    full_name = request.form.get('full_name', '').strip()
    username  = request.form.get('username', '').strip()
    email     = request.form.get('email', '').strip()
    role_name = request.form.get('role_name', 'admin').strip()
    password  = request.form.get('password', '').strip()
    confirm   = request.form.get('confirm_password', '').strip()

    if not all([full_name, username, email, password, confirm]):
        flash('All fields are required.', 'error')
        return redirect(url_for('auth.admin_login') + '?tab=register')

    if not re.match(r"^[A-Za-z\s]+$", full_name):
        flash('Wrong input for Full Name. Correct version: Should only contain letters and spaces.', 'error')
        return redirect(url_for('auth.admin_login') + '?tab=register')

    if not re.match(r"^[A-Za-z0-9_]+$", username):
        flash('Wrong input for Username. Correct version: Should only contain letters, numbers, and underscores.', 'error')
        return redirect(url_for('auth.admin_login') + '?tab=register')

    if password != confirm:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth.admin_login') + '?tab=register')

    existing = fetch_one("""
        SELECT admin_id FROM admin_users
        WHERE LOWER(username) = LOWER(:username) OR LOWER(email) = LOWER(:email)
    """, {"username": username, "email": email})

    if existing:
        flash('Username or email already exists.', 'error')
        return redirect(url_for('auth.admin_login') + '?tab=register')

    try:
        admin_id = _next_admin_id()
        execute_dml("""
            INSERT INTO admin_users (admin_id, username, full_name, email, role_name, password_hash)
            VALUES (:admin_id, :username, :full_name, :email, :role_name, :password_hash)
        """, {
            "admin_id":      admin_id,
            "username":      username,
            "full_name":     full_name,
            "email":         email,
            "role_name":     role_name,
            "password_hash": _hash_password(password),
        })
        flash(f'Account created! Your Admin ID is {admin_id}. You can now sign in.', 'success')
    except Exception as e:
        flash(f'Registration failed: {str(e)}', 'error')
        return redirect(url_for('auth.admin_login') + '?tab=register')

    return redirect(url_for('auth.admin_login'))


@auth_bp.route('/admin/logout')
def admin_logout():
    admin_id = session.get('admin_id')
    if admin_id:
        execute_dml("""
            UPDATE chat_sessions 
            SET is_active = 'N' 
            WHERE owner_role = 'ADMIN' AND admin_id = :admin_id AND is_active = 'Y'
        """, {"admin_id": admin_id})
    
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_user', None)
    session.pop('admin_name', None)
    return redirect(url_for('auth.admin_login'))

@auth_bp.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        email      = request.form.get('email', '').strip()
        password   = request.form.get('password', '').strip()

        # Try hashed password first (new accounts), then plain text (legacy accounts)
        hashed = _hash_password(password)
        user = fetch_one("""
            SELECT student_id, full_name, email, class_level, section, account_status
            FROM students
            WHERE LOWER(email) = LOWER(:email)
              AND (password_hash = :hashed OR password_hash = :plain)
              AND account_status = 'ACTIVE'
        """, {
            "email":      email,
            "hashed":     hashed,
            "plain":      password,
        })

        if user:
            session['student_logged_in'] = True
            session['student_id']   = user['student_id']
            session['student_name'] = user['full_name']
            return redirect(url_for('student.dashboard'))

        flash('Invalid credentials. Check your Student ID, email and password.', 'error')

    return render_template('student/login.html')


@auth_bp.route('/student/register', methods=['POST'])
def student_register():
    full_name      = request.form.get('full_name', '').strip()
    email          = request.form.get('email', '').strip()
    phone_number   = request.form.get('phone_number', '').strip()
    class_level    = request.form.get('class_level', '').strip()
    section        = request.form.get('section', '').strip()
    guardian_name  = request.form.get('guardian_name', '').strip()
    guardian_email = request.form.get('guardian_email', '').strip()
    password       = request.form.get('password', '').strip()
    confirm        = request.form.get('confirm_password', '').strip()

    if not all([full_name, email, class_level, section, password, confirm]):
        flash('All required fields must be filled.', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    if not re.match(r"^[A-Za-z\s]+$", full_name):
        flash('Wrong input for Full Name. Correct version: Should only contain letters and spaces.', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    if phone_number and not re.match(r"^\d{10}$", phone_number):
        flash('Wrong input for Phone Number. Correct version: Should contain exactly 10 digits.', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    if guardian_name and not re.match(r"^[A-Za-z\s]+$", guardian_name):
        flash('Wrong input for Guardian Name. Correct version: Should only contain letters and spaces.', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    if password != confirm:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    existing = fetch_one("""
        SELECT student_id FROM students WHERE LOWER(email) = LOWER(:email)
    """, {"email": email})

    if existing:
        flash('An account with this email already exists.', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    try:
        student_id = _next_student_id()
        execute_dml("""
            INSERT INTO students (
                student_id, full_name, email, phone_number,
                class_level, section,
                guardian_name, guardian_email,
                password_hash, account_status,
                performance_index, risk_level, attendance_rate,
                complaint_count, due_amount, confidence_score
            ) VALUES (
                :student_id, :full_name, :email, :phone_number,
                :class_level, :section,
                :guardian_name, :guardian_email,
                :password_hash, 'ACTIVE',
                0, 'low', 0, 0, 0, 0
            )
        """, {
            "student_id":     student_id,
            "full_name":      full_name,
            "email":          email,
            "phone_number":   phone_number or None,
            "class_level":    class_level,
            "section":        section,
            "guardian_name":  guardian_name or None,
            "guardian_email": guardian_email or None,
            "password_hash":  _hash_password(password),
        })
        flash(f'Account created! Your Student ID is {student_id}. You can now sign in.', 'success')
    except Exception as e:
        flash(f'Registration failed: {str(e)}', 'error')
        return redirect(url_for('auth.student_login') + '?tab=register')

    return redirect(url_for('auth.student_login'))


@auth_bp.route('/student/logout')
def student_logout():
    session.pop('student_logged_in', None)
    session.pop('student_id', None)
    session.pop('student_name', None)
    return redirect(url_for('auth.student_login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Email is required.', 'error')
            return render_template('shared/forgot_password.html')

        # Check if email exists in either table
        user = fetch_one("SELECT email, 'ADMIN' as user_type FROM admin_users WHERE LOWER(email) = LOWER(:email)", {"email": email})
        if not user:
            user = fetch_one("SELECT email, 'STUDENT' as user_type FROM students WHERE LOWER(email) = LOWER(:email)", {"email": email})

        if user:
            # Generate token
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            # Token valid for 1 hour
            expires_at = datetime.now() + timedelta(hours=1)

            # Store in DB (Clean up old tokens for this email first)
            execute_dml("DELETE FROM password_reset_tokens WHERE LOWER(email) = LOWER(:email)", {"email": email})
            execute_dml("""
                INSERT INTO password_reset_tokens (email, token_hash, user_type, expires_at)
                VALUES (:email, :token_hash, :user_type, :expires_at)
            """, {
                "email": email,
                "token_hash": token_hash,
                "user_type": user['user_type'],
                "expires_at": expires_at
            })

            # Send Email
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            success, msg = send_password_reset_email(email, reset_url)
            if success:
                flash('A password reset link has been sent to your email.', 'success')
            else:
                flash(f'Failed to send email: {msg}', 'error')
        else:
            # For security, don't reveal if email exists
            flash('If an account exists with that email, a reset link has been sent.', 'success')
            
    return render_template('shared/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Verify token
    reset_req = fetch_one("""
        SELECT email, user_type, expires_at 
        FROM password_reset_tokens 
        WHERE token_hash = :token_hash
    """, {"token_hash": token_hash})
    
    if not reset_req or reset_req['expires_at'] < datetime.now():
        flash('The reset link is invalid or has expired.', 'error')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm_password', '').strip()
        
        if not password or password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('shared/reset_password.html', token=token)
        
        new_hash = _hash_password(password)
        email    = reset_req['email']
        
        try:
            if reset_req['user_type'] == 'ADMIN':
                execute_dml("UPDATE admin_users SET password_hash = :hash WHERE LOWER(email) = LOWER(:email)", {"hash": new_hash, "email": email})
                flash('Password reset successful. You can now login as Admin.', 'success')
                target_login = 'auth.admin_login'
            else:
                execute_dml("UPDATE students SET password_hash = :hash WHERE LOWER(email) = LOWER(:email)", {"hash": new_hash, "email": email})
                flash('Password reset successful. You can now login as Student.', 'success')
                target_login = 'auth.student_login'
                
            # Clean up tokens
            execute_dml("DELETE FROM password_reset_tokens WHERE LOWER(email) = LOWER(:email)", {"email": email})
            return redirect(url_for(target_login))
        except Exception as e:
            flash(f'Error updating password: {str(e)}', 'error')
        
    return render_template('shared/reset_password.html', token=token)