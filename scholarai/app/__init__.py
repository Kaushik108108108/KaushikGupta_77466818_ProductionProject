# This file initializes the Flask application and sets up all necessary extensions and routes.
import os
from dotenv import load_dotenv
from flask import Flask, jsonify

from .routes.auth import auth_bp
from .routes.admin import admin_bp
from .routes.student import student_bp
from .db import init_db, close_db, fetch_one
from .extensions import mail

# The create_app function is the factory that constructs the entire ScholarAI application.
def create_app():
    # Load environment variables from the .env file for configuration.
    load_dotenv()

    # Create the Flask app instance.
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "scholarai-secret-key-change-in-production")
    
    # Configure the mail server settings for sending system emails and alerts.
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Initialize the mail extension with our app configuration.
    mail.init_app(app)

    # Initialize the database connection pool.
    init_db()
    # Ensure database connections are properly closed when the application shuts down.
    app.teardown_appcontext(close_db)

    # Register blueprints to organize our routes into distinct modules (Auth, Admin, Student).
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    # A simple health check route to verify that the database is connected and responding.
    @app.get("/health/db")
    def db_health():
        row = fetch_one("SELECT 'OK' AS status FROM dual")
        return jsonify(row), 200

    return app