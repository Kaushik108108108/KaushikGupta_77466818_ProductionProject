# We import the necessary tools to build our web application.
import os
from dotenv import load_dotenv
from flask import Flask, jsonify

from .routes.auth import auth_bp
from .routes.admin import admin_bp
from .routes.student import student_bp
from .db import init_db, close_db, fetch_one
from .extensions import mail

# This is the main function that creates and sets up our entire application.
def create_app():
    # We load our secret settings from the environment variables.
    load_dotenv()

    # We start the Flask application and give it a secret key for security.
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "scholarai-secret-key-change-in-production")
    
    # Here we set up the email system so the portal can send notifications and alerts.
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
    
    mail.init_app(app)

    # We initialize the connection to our database.
    init_db()
    # We make sure the database connection closes safely when the application stops.
    app.teardown_appcontext(close_db)

    # We register the different parts of our website, like the login pages, admin area, and student portal.
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')

    # This is a simple check to see if the database is running correctly.
    @app.get("/health/db")
    def db_health():
        row = fetch_one("SELECT 'OK' AS status FROM dual")
        return jsonify(row), 200

    return app