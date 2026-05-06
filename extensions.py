"""
Flask extensions for The Eagle Biology Class LMS
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialize database
db = SQLAlchemy()

# Initialize login manager
login_manager = LoginManager()

# Set login view (redirect to login page if not authenticated)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
