"""
Script to initialize the Admin user
Run this once to create the default administrator.
"""
import sys
import os
from datetime import datetime

# Ensure the app can be found
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the app, db, and User model from your main application file
# NOTE: If your file is named something other than 'app.py', change 'app' below to match.
try:
    from app import app, db
    from models import User
except ImportError:
    print("Error: Could not import app or models. Make sure this script is in the same folder as your application file (likely app.py).")
    sys.exit(1)

def create_admin():
    with app.app_context():
        # Check if admin already exists to prevent duplicates
        existing_admin = User.query.filter_by(username='admin@cks.com').first()
        if existing_admin:
            print("Admin user 'admin@cks.com' already exists.")
            choice = input("Do you want to reset the password for this user? (y/n): ").lower()
            if choice == 'y':
                existing_admin.set_password('admin123')
                db.session.commit()
                print("Admin password has been reset to 'admin123'.")
            else:
                print("No changes made.")
            return

        # Create the admin user
        # Note: In your model, 'username' is used as the email field.
        # Note: date_of_birth is required in your model, so we provide a dummy date
        admin_user = User(
            username='admin@cks.com',
            first_name='System',
            last_name='Administrator',
            date_of_birth=datetime(2000, 1, 1),
            user_type='admin'
        )

        # Set the password (this hashes it automatically)
        admin_user.set_password('admin123')

        try:
            db.session.add(admin_user)
            db.session.commit()
            print("------------------------------------------------")
            print("Admin user created successfully!")
            print("Email/Username: admin@cks.com")
            print("Password: admin123")
            print("------------------------------------------------")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin: {e}")

if __name__ == '__main__':
    create_admin()