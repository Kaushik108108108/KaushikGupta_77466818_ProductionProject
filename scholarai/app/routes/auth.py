from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.db import fetch_one

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    return render_template('shared/index.html')

@auth_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        login = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = fetch_one("""
            SELECT admin_id, username, full_name, email, role_name
            FROM admin_users
            WHERE (LOWER(username) = LOWER(:login) OR LOWER(email) = LOWER(:login))
              AND password_hash = :password
        """, {"login": login, "password": password})

        if user:
            session['admin_logged_in'] = True
            session['admin_id'] = user['admin_id']
            session['admin_user'] = user['username']
            session['admin_name'] = user['full_name']
            return redirect(url_for('admin.dashboard'))

        flash('Invalid username or password.', 'error')

    return render_template('admin/login.html')

@auth_bp.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_id', None)
    session.pop('admin_user', None)
    session.pop('admin_name', None)
    return redirect(url_for('auth.admin_login'))

@auth_bp.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        student_id = request.form.get('student_id', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        user = fetch_one("""
            SELECT student_id, full_name, email, class_level, section, account_status
            FROM students
            WHERE student_id = :student_id
              AND LOWER(email) = LOWER(:email)
              AND password_hash = :password
              AND account_status = 'ACTIVE'
        """, {
            "student_id": student_id,
            "email": email,
            "password": password
        })

        if user:
            session['student_logged_in'] = True
            session['student_id'] = user['student_id']
            session['student_name'] = user['full_name']
            return redirect(url_for('student.dashboard'))

        flash('Invalid credentials. Check your Student ID, email and password.', 'error')

    return render_template('student/login.html')

@auth_bp.route('/student/logout')
def student_logout():
    session.pop('student_logged_in', None)
    session.pop('student_id', None)
    session.pop('student_name', None)
    return redirect(url_for('auth.student_login'))