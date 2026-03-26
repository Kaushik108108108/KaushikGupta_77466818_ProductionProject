import os
from dotenv import load_dotenv
from flask import Flask, jsonify

from .routes.auth import auth_bp
from .routes.admin import admin_bp
from .routes.student import student_bp
from .db import init_db, close_db, fetch_one

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "scholarai-secret-key-change-in-production")

    init_db()
    app.teardown_appcontext(close_db)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    @app.get("/health/db")
    def db_health():
        row = fetch_one("SELECT 'OK' AS status FROM dual")
        return jsonify(row), 200

    return app