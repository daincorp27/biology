"""
Configuration for The Eagle Biology Class LMS
"""
import os

class Config:
    """Base configuration"""
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'st-georges-biology-secret-key-change-in-production'

    # Database URI - SQLite by default, PostgreSQL-ready
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///biology_lms.db'

    # Track modifications (disable for performance)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # File upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size

    # Allowed file extensions for uploads
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'mp4', 'mp3', 'wav', 'webm', 'ogg', 'm4a', 'jpg', 'jpeg', 'png', 'gif'}

    # Live class settings
    LIVE_CLASS_DURATION_MINUTES = 60

    # Debug mode can be controlled with FLASK_DEBUG or DEBUG environment variables
    DEBUG = os.environ.get('FLASK_DEBUG', os.environ.get('DEBUG', 'false')).lower() in ['1', 'true', 'yes']
