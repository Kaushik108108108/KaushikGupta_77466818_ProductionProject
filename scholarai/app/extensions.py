# This file initializes the extensions we use in our application.
from flask_mail import Mail

# We create a shared email tool that can be used across different parts of the website.
mail = Mail()
