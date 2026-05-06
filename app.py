"""
The Eagle Biology Class - Learning Management System
A Flask-based LMS for Biology education
"""
import os
from dotenv import load_dotenv
import requests

# Load environment variables from .env before config is imported
load_dotenv()

# Only set proxy if explicitly configured in environment.
proxy_url = os.getenv("PROXY_URL", "").strip()
if proxy_url:
    os.environ["https_proxy"] = proxy_url
    os.environ["http_proxy"] = proxy_url
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from sqlalchemy import inspect, text, or_
import os
import uuid
from functools import wraps
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
# Import configuration and extensions
from config import Config
from extensions import db, login_manager
from models import (
    User, Course, Module, Topic, Lesson, Enrollment,
    Quiz, QuizQuestion, QuizSubmission, QuizAnswer,
    Essay, EssaySubmission,
    LiveClass, Discussion, Reply,
    Notification, LibraryResource,
    StudentQuestion, TeacherAnswer
)
from ai_pool_manager import ai_pool

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)

# Create upload folders if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files'), exist_ok=True)


def _preview_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'])


def build_preview_token(resource_id, user_id):
    return _preview_serializer().dumps({"rid": resource_id, "uid": user_id})


def validate_preview_token(token, resource_id, user_id, max_age_seconds=3600):
    if not token:
        return False
    try:
        data = _preview_serializer().loads(token, max_age=max_age_seconds)
    except (BadSignature, SignatureExpired):
        return False
    return data.get("rid") == resource_id and data.get("uid") == user_id


# ================================
# LOGIN MANAGER USER LOADER
# ================================

@login_manager.user_loader
def load_user(user_id):
    """Load user for Flask-Login"""
    return db.session.get(User, int(user_id))

# ================================
# ROLE-BASED ACCESS CONTROL DECORATORS
# ================================

def admin_required(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Decorator to restrict access to teacher users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher:
            flash('Access denied. Teacher privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator to restrict access to student users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_student:
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ================================
# HELPER FUNCTIONS
# ================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def calculate_grade_percentage(score, max_score):
    """Calculate percentage grade"""
    if max_score == 0:
        return 0
    return round((score / max_score) * 100, 2)

# ================================
# CONTEXT PROCESSOR
# ================================

@app.context_processor
def inject_now():
    """Inject current datetime into all templates"""
    return dict(now=datetime.now())

# ================================
# ROUTES
# ================================

# AUTHENTICATION ROUTES

@app.route('/')
def index():
    """Landing page"""
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    User registration
    Allows registration for all user roles
    """
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date_of_birth = request.form.get('date_of_birth')
        user_type = request.form.get('user_type')

        # Validation
        if not all([username, password, first_name, last_name, date_of_birth, user_type]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('register'))

        if user_type not in ['admin', 'teacher', 'student']:
            flash('Invalid user type selected.', 'danger')
            return redirect(url_for('register'))

        try:
            # Create new user
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d'),
                user_type=user_type
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    User login
    Supports all user roles with role-based redirection
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user
        user = User.query.filter_by(username=username).first()

        # Check credentials
        if user and user.check_password(password):
            login_user(user)

            # Redirect based on user role
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            elif user.is_teacher:
                return redirect(url_for('teacher_dashboard'))
            else:  # student
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Dedicated admin login page
    Only admins can login through this route
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user
        user = User.query.filter_by(username=username).first()

        # Check credentials and verify it's an admin
        if user and user.check_password(password) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials. Access denied.', 'danger')

    return render_template('admin/login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


# DASHBOARDS

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard with role-based redirection
    """
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    elif current_user.is_teacher:
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))


@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """
    Account settings page for updating login email, name, and password.
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([email, first_name, last_name, current_password]):
            flash('Please fill in all required fields and enter your current password.', 'danger')
            return redirect(url_for('settings'))

        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('settings'))

        if email != current_user.username:
            if User.query.filter(User.username == email, User.id != current_user.id).first():
                flash('This email is already registered. Please choose a different one.', 'danger')
                return redirect(url_for('settings'))
            current_user.username = email

        current_user.first_name = first_name
        current_user.last_name = last_name

        if new_password:
            if new_password != confirm_password:
                flash('New password and confirmation do not match.', 'danger')
                return redirect(url_for('settings'))
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long.', 'danger')
                return redirect(url_for('settings'))
            current_user.set_password(new_password)

        try:
            db.session.commit()
            flash('Your account settings have been updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Unable to update settings: {str(e)}', 'danger')

        return redirect(url_for('settings'))

    return render_template('settings.html')


@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    """
    Admin dashboard
    Overview of system statistics and management options
    """
    # Statistics
    total_users = User.query.count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.filter_by(status='approved').count()

    # Recent enrollments
    recent_enrollments = Enrollment.query.filter_by(status='pending').limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_courses=total_courses,
                           total_enrollments=total_enrollments,
                           recent_enrollments=recent_enrollments)


@app.route('/teacher/dashboard')
@login_required
@teacher_required
def teacher_dashboard():
    """
    Teacher dashboard
    Overview of courses, students, and assignments
    """
    # Get courses taught by this teacher
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

    # Calculate total students across all courses
    total_students = sum([course.enrolled_count for course in courses])

    # Pending enrollment requests
    course_ids = [course.id for course in courses]
    pending_enrollments = Enrollment.query.filter(
        Enrollment.course_id.in_(course_ids),
        Enrollment.status == 'pending'
    ).all() if course_ids else []

    return render_template('teacher/dashboard.html',
                           courses=courses,
                           total_students=total_students,
                           pending_enrollments=pending_enrollments)


@app.route('/student/dashboard')
@login_required
@student_required
def student_dashboard():
    """
    Student dashboard
    Overview of enrolled courses, assignments, and notifications
    """
    # Get approved enrollments
    enrollments = Enrollment.query.filter_by(
        student_id=current_user.id,
        status='approved'
    ).all()

    courses = [enrollment.course for enrollment in enrollments]

    # Get unread notifications
    notifications = Notification.query.filter_by(
        recipient_id=current_user.id,
        is_visible=True
    ).order_by(Notification.created_at.desc()).limit(10).all()

    # Unread count
    unread_count = len([n for n in notifications if not n.is_read])

    return render_template('student/dashboard.html',
                           courses=courses,
                           notifications=notifications,
                           unread_count=unread_count)


# COURSE MANAGEMENT

@app.route('/courses')
@login_required
def courses_list():
    """
    View all courses
    Admin: See all courses
    Teacher: See own courses
    Student: See available courses for enrollment
    """
    if current_user.is_admin:
        courses = Course.query.all()
    elif current_user.is_teacher:
        courses = Course.query.filter_by(teacher_id=current_user.id).all()
    else:  # student
        courses = Course.query.all()

    return render_template('courses/list.html', courses=courses)


@app.route('/courses/<int:course_id>')
@login_required
def course_detail(course_id):
    """
    View course details
    Shows curriculum, assignments, and basic info
    """
    course = Course.query.get_or_404(course_id)

    # Check access permission
    if current_user.is_student and not current_user.can_access_course(course_id):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('courses_list'))

    # Get curriculum
    modules = Module.query.filter_by(course_id=course_id).order_by(Module.order).all()

    # Get assignments
    quizzes = Quiz.query.filter_by(course_id=course_id).all()
    essays = Essay.query.filter_by(course_id=course_id).all()

    # Get live classes
    live_classes = LiveClass.query.filter_by(course_id=course_id).order_by(LiveClass.created_at.desc()).all()

    # Get discussions
    discussions = Discussion.query.filter_by(course_id=course_id).order_by(Discussion.is_pinned.desc(), Discussion.created_at.desc()).all()

    return render_template('courses/detail.html',
                           course=course,
                           modules=modules,
                           quizzes=quizzes,
                           essays=essays,
                           live_classes=live_classes,
                           discussions=discussions)


@app.route('/admin/courses/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_course():
    """
    Create a new course (admin only)
    Assigns a teacher to the course
    """
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        target_level = request.form.get('target_level')
        max_students = request.form.get('max_students', 50)
        teacher_id = request.form.get('teacher_id')

        # Validation
        if not all([title, description, target_level, teacher_id]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('create_course'))

        if target_level not in ['Lower Secondary', 'Advanced Level']:
            flash('Invalid target level selected.', 'danger')
            return redirect(url_for('create_course'))

        # Verify teacher exists
        teacher = User.query.filter_by(id=teacher_id, user_type='teacher').first()
        if not teacher:
            flash('Invalid teacher selected.', 'danger')
            return redirect(url_for('create_course'))

        try:
            course = Course(
                title=title,
                description=description,
                target_level=target_level,
                max_students=int(max_students),
                teacher_id=teacher_id
            )

            db.session.add(course)
            db.session.commit()

            flash(f'Course "{title}" created successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create course: {str(e)}', 'danger')
            return redirect(url_for('create_course'))

    # Get all teachers for dropdown
    teachers = User.query.filter_by(user_type='teacher').all()

    return render_template('courses/create.html', teachers=teachers)


@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    """
    Edit an existing course (admin only)
    """
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        target_level = request.form.get('target_level')
        max_students = request.form.get('max_students', 50)
        teacher_id = request.form.get('teacher_id')

        # Validation: Removed teacher_id from required fields check
        if not all([title, description, target_level]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('edit_course', course_id=course_id))

        if target_level not in ['Lower Secondary', 'Advanced Level']:
            flash('Invalid target level selected.', 'danger')
            return redirect(url_for('edit_course', course_id=course_id))

        # Verify teacher exists ONLY if a teacher was selected
        assigned_teacher_id = None
        if teacher_id:
            teacher = User.query.filter_by(id=teacher_id, user_type='teacher').first()
            if not teacher:
                flash('Invalid teacher selected.', 'danger')
                return redirect(url_for('edit_course', course_id=course_id))
            assigned_teacher_id = teacher.id

        try:
            course.title = title
            course.description = description
            course.target_level = target_level
            course.max_students = int(max_students)
            course.teacher_id = assigned_teacher_id  # Can be None

            db.session.commit()

            flash(f'Course "{title}" updated successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update course: {str(e)}', 'danger')
            return redirect(url_for('edit_course', course_id=course_id))

    # Get all teachers for dropdown
    teachers = User.query.filter_by(user_type='teacher').all()

    return render_template('courses/edit.html', course=course, teachers=teachers)

@app.route('/admin/courses/<int:course_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    """
    Delete a course (admin only)
    Cascades delete to all related data
    """
    course = Course.query.get_or_404(course_id)

    try:
        db.session.delete(course)
        db.session.commit()
        flash(f'Course "{course.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete course: {str(e)}', 'danger')

    return redirect(url_for('courses_list'))


# PAYMENT SYSTEM

@app.route('/student/payment', methods=['GET', 'POST'])
@login_required
@student_required
def make_payment():
    """
    Simulated payment route for students
    Sets has_paid flag to True upon "payment"
    """
    if current_user.has_paid:
        flash('You have already paid for your courses.', 'info')
        return redirect(url_for('student_dashboard'))

    if request.method == 'POST':
        # Simulate payment processing
        card_number = request.form.get('card_number')
        card_holder = request.form.get('card_holder')
        expiry = request.form.get('expiry')
        cvv = request.form.get('cvv')

        # Basic validation (in production, integrate with actual payment gateway)
        if not all([card_number, card_holder, expiry, cvv]):
            flash('Please fill in all payment details.', 'danger')
            return redirect(url_for('make_payment'))

        try:
            # Set payment status to paid
            current_user.has_paid = True
            db.session.commit()

            flash('Payment successful! You can now enroll in courses.', 'success')
            return redirect(url_for('student_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Payment failed: {str(e)}', 'danger')
            return redirect(url_for('make_payment'))

    return render_template('student/payment.html')


# ENROLLMENT SYSTEM

@app.route('/student/courses/<int:course_id>/enroll', methods=['POST'])
@login_required
@student_required
def request_enrollment(course_id):
    """
    Student requests enrollment in a course
    Requires has_paid to be True
    Prevents duplicate enrollments
    """
    course = Course.query.get_or_404(course_id)

    # Check if student has paid
    if not current_user.has_paid:
        flash('Please complete payment before enrolling in courses.', 'warning')
        return redirect(url_for('make_payment'))

    # Check if already enrolled
    existing_enrollment = Enrollment.query.filter_by(
        student_id=current_user.id,
        course_id=course_id
    ).first()

    if existing_enrollment:
        flash(f'You already have a {existing_enrollment.status} enrollment request for this course.', 'info')
        return redirect(url_for('courses_list'))

    # Check if course is full
    if course.is_full:
        flash('This course is currently full. Please try again later.', 'warning')
        return redirect(url_for('courses_list'))

    try:
        # Create enrollment request
        enrollment = Enrollment(
            student_id=current_user.id,
            course_id=course_id,
            status='pending'
        )

        db.session.add(enrollment)
        db.session.commit()

        flash(f'Enrollment request sent for "{course.title}". The teacher will review your request.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to request enrollment: {str(e)}', 'danger')

    return redirect(url_for('courses_list'))


@app.route('/teacher/enrollments/<int:enrollment_id>/approve', methods=['POST'])
@login_required
@teacher_required
def approve_enrollment(enrollment_id):
    """
    Teacher approves student enrollment
    Checks teacher owns the course
    """
    enrollment = Enrollment.query.get_or_404(enrollment_id)

    # Check if teacher owns the course
    if enrollment.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    try:
        enrollment.status = 'approved'
        enrollment.responded_at = datetime.utcnow()
        db.session.commit()

        flash(f'Approved {enrollment.student.full_name} for "{enrollment.course.title}".', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to approve enrollment: {str(e)}', 'danger')

    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/enrollments/<int:enrollment_id>/decline', methods=['POST'])
@login_required
@teacher_required
def decline_enrollment(enrollment_id):
    """
    Teacher declines student enrollment
    Checks teacher owns the course
    """
    enrollment = Enrollment.query.get_or_404(enrollment_id)

    # Check if teacher owns the course
    if enrollment.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    try:
        enrollment.status = 'declined'
        enrollment.responded_at = datetime.utcnow()
        db.session.commit()

        flash(f'Declined {enrollment.student.full_name} for "{enrollment.course.title}".', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to decline enrollment: {str(e)}', 'danger')

    return redirect(url_for('teacher_dashboard'))


@app.route('/admin/enrollments/<int:enrollment_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_approve_enrollment(enrollment_id):
    """
    Admin approves student enrollment (override)
    """
    enrollment = Enrollment.query.get_or_404(enrollment_id)

    try:
        enrollment.status = 'approved'
        enrollment.responded_at = datetime.utcnow()
        db.session.commit()

        flash(f'Approved {enrollment.student.full_name} for "{enrollment.course.title}".', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to approve enrollment: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/enrollments/<int:enrollment_id>/decline', methods=['POST'])
@login_required
@admin_required
def admin_decline_enrollment(enrollment_id):
    """
    Admin declines student enrollment (override)
    """
    enrollment = Enrollment.query.get_or_404(enrollment_id)

    try:
        enrollment.status = 'declined'
        enrollment.responded_at = datetime.utcnow()
        db.session.commit()

        flash(f'Declined {enrollment.student.full_name} for "{enrollment.course.title}".', 'info')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to decline enrollment: {str(e)}', 'danger')

    return redirect(url_for('admin_dashboard'))


# CURRICULUM STRUCTURE (MODULES, TOPICS, LESSONS)

# MODULE ROUTES

@app.route('/teacher/courses/<int:course_id>/modules/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_module(course_id):
    """
    Create a module within a course (teacher only)
    Teacher must own the course
    """
    course = Course.query.get_or_404(course_id)

    # Check if teacher owns the course
    if course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        order = request.form.get('order', 0)

        if not title:
            flash('Module title is required.', 'danger')
            return redirect(url_for('create_module', course_id=course_id))

        try:
            module = Module(
                title=title,
                description=description,
                order=int(order),
                course_id=course_id
            )

            db.session.add(module)
            db.session.commit()

            flash(f'Module "{title}" created successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create module: {str(e)}', 'danger')
            return redirect(url_for('create_module', course_id=course_id))

    return render_template('curriculum/create_module.html', course=course)


@app.route('/teacher/modules/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_module(module_id):
    """
    Edit a module (teacher only)
    Teacher must own the course
    """
    module = Module.query.get_or_404(module_id)

    # Check if teacher owns the course
    if module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        order = request.form.get('order', 0)

        if not title:
            flash('Module title is required.', 'danger')
            return redirect(url_for('edit_module', module_id=module_id))

        try:
            module.title = title
            module.description = description
            module.order = int(order)

            db.session.commit()

            flash(f'Module "{title}" updated successfully!', 'success')
            return redirect(url_for('course_detail', course_id=module.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update module: {str(e)}', 'danger')
            return redirect(url_for('edit_module', module_id=module_id))

    return render_template('curriculum/edit_module.html', module=module)


@app.route('/teacher/modules/<int:module_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_module(module_id):
    """
    Delete a module (teacher only)
    Cascades delete to topics and lessons
    """
    module = Module.query.get_or_404(module_id)

    # Check if teacher owns the course
    if module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    try:
        course_id = module.course_id
        db.session.delete(module)
        db.session.commit()
        flash(f'Module "{module.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete module: {str(e)}', 'danger')

    return redirect(url_for('course_detail', course_id=course_id))


# TOPIC ROUTES

@app.route('/teacher/modules/<int:module_id>/topics/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_topic(module_id):
    """
    Create a topic within a module (teacher only)
    """
    module = Module.query.get_or_404(module_id)

    # Check if teacher owns the course
    if module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        order = request.form.get('order', 0)

        if not title:
            flash('Topic title is required.', 'danger')
            return redirect(url_for('create_topic', module_id=module_id))

        try:
            topic = Topic(
                title=title,
                description=description,
                order=int(order),
                module_id=module_id
            )

            db.session.add(topic)
            db.session.commit()

            flash(f'Topic "{title}" created successfully!', 'success')
            return redirect(url_for('course_detail', course_id=module.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create topic: {str(e)}', 'danger')
            return redirect(url_for('create_topic', module_id=module_id))

    return render_template('curriculum/create_topic.html', module=module)


@app.route('/teacher/topics/<int:topic_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_topic(topic_id):
    """
    Edit a topic (teacher only)
    """
    topic = Topic.query.get_or_404(topic_id)

    # Check if teacher owns the course
    if topic.module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        order = request.form.get('order', 0)

        if not title:
            flash('Topic title is required.', 'danger')
            return redirect(url_for('edit_topic', topic_id=topic_id))

        try:
            topic.title = title
            topic.description = description
            topic.order = int(order)

            db.session.commit()

            flash(f'Topic "{title}" updated successfully!', 'success')
            return redirect(url_for('course_detail', course_id=topic.module.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update topic: {str(e)}', 'danger')
            return redirect(url_for('edit_topic', topic_id=topic_id))

    return render_template('curriculum/edit_topic.html', topic=topic)


@app.route('/teacher/topics/<int:topic_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_topic(topic_id):
    """
    Delete a topic (teacher only)
    Cascades delete to lessons
    """
    topic = Topic.query.get_or_404(topic_id)

    # Check if teacher owns the course
    if topic.module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    try:
        course_id = topic.module.course_id
        db.session.delete(topic)
        db.session.commit()
        flash(f'Topic "{topic.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete topic: {str(e)}', 'danger')

    return redirect(url_for('course_detail', course_id=course_id))


# LESSON ROUTES

@app.route('/editor/upload', methods=['POST'])
@login_required
@teacher_required
def editor_upload():
    """
    Handles file uploads from the Quill.js editor.
    Used for images and videos inserted directly into the text.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Create a unique filename to prevent overwrites
        ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"

        try:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            # Return the URL to the file
            file_url = url_for('uploaded_file', filename=unique_filename)
            return jsonify({'location': file_url})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'File type not allowed'}), 400


@app.route('/teacher/topics/<int:topic_id>/lessons/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_lesson(topic_id):
    """
    Create a lesson within a topic (teacher only)
    Supports biology theory, videos, images, and lab lessons
    """
    topic = Topic.query.get_or_404(topic_id)

    # Check if teacher owns the course
    if topic.module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        theory_text = request.form.get('theory_text')
        video_url = request.form.get('video_url')
        is_lab_lesson = request.form.get('is_lab_lesson') == 'on'
        order = request.form.get('order', 0)

        # Handle file uploads
        video_file = None
        image_files = []

        if 'video_file' in request.files and request.files['video_file'].filename:
            video_upload = request.files['video_file']
            if allowed_file(video_upload.filename):
                video_filename = secure_filename(f"{datetime.utcnow().timestamp()}_{video_upload.filename}")
                video_upload.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))
                video_file = video_filename

        if 'image_files' in request.files:
            image_uploads = request.files.getlist('image_files')
            for img in image_uploads:
                if img.filename and allowed_file(img.filename):
                    img_filename = secure_filename(f"{datetime.utcnow().timestamp()}_{img.filename}")
                    img.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
                    image_files.append(img_filename)

        if not title:
            flash('Lesson title is required.', 'danger')
            return redirect(url_for('create_lesson', topic_id=topic_id))

        try:
            lesson = Lesson(
                title=title,
                description=description,
                theory_text=theory_text,
                video_url=video_url,
                video_file=video_file,
                image_files=','.join(image_files) if image_files else None,
                is_lab_lesson=is_lab_lesson,
                order=int(order),
                topic_id=topic_id
            )

            db.session.add(lesson)
            db.session.commit()

            flash(f'Lesson "{title}" created successfully!', 'success')
            return redirect(url_for('course_detail', course_id=topic.module.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create lesson: {str(e)}', 'danger')
            return redirect(url_for('create_lesson', topic_id=topic_id))

    return render_template('curriculum/create_lesson.html', topic=topic)


@app.route('/teacher/lessons/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
@teacher_required
def edit_lesson(lesson_id):
    """
    Edit a lesson (teacher only)
    """
    lesson = Lesson.query.get_or_404(lesson_id)

    # Check if teacher owns the course
    if lesson.topic.module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        theory_text = request.form.get('theory_text')
        video_url = request.form.get('video_url')
        is_lab_lesson = request.form.get('is_lab_lesson') == 'on'
        order = request.form.get('order', 0)

        # Handle file uploads
        video_file = lesson.video_file  # Keep existing if no new upload
        image_files = lesson.image_files.split(',') if lesson.image_files else []

        if 'video_file' in request.files and request.files['video_file'].filename:
            video_upload = request.files['video_file']
            if allowed_file(video_upload.filename):
                video_filename = secure_filename(f"{datetime.utcnow().timestamp()}_{video_upload.filename}")
                video_upload.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))
                video_file = video_filename

        if 'image_files' in request.files:
            image_uploads = request.files.getlist('image_files')
            for img in image_uploads:
                if img.filename and allowed_file(img.filename):
                    img_filename = secure_filename(f"{datetime.utcnow().timestamp()}_{img.filename}")
                    img.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
                    image_files.append(img_filename)

        if not title:
            flash('Lesson title is required.', 'danger')
            return redirect(url_for('edit_lesson', lesson_id=lesson_id))

        try:
            lesson.title = title
            lesson.description = description
            lesson.theory_text = theory_text
            lesson.video_url = video_url
            lesson.video_file = video_file
            lesson.image_files = ','.join(image_files) if image_files else None
            lesson.is_lab_lesson = is_lab_lesson
            lesson.order = int(order)

            db.session.commit()

            flash(f'Lesson "{title}" updated successfully!', 'success')
            return redirect(url_for('course_detail', course_id=lesson.topic.module.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update lesson: {str(e)}', 'danger')
            return redirect(url_for('edit_lesson', lesson_id=lesson_id))

    return render_template('curriculum/edit_lesson.html', lesson=lesson)


@app.route('/teacher/lessons/<int:lesson_id>/delete', methods=['POST'])
@login_required
@teacher_required
def delete_lesson(lesson_id):
    """
    Delete a lesson (teacher only)
    """
    lesson = Lesson.query.get_or_404(lesson_id)

    # Check if teacher owns the course
    if lesson.topic.module.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    try:
        course_id = lesson.topic.module.course_id
        db.session.delete(lesson)
        db.session.commit()
        flash(f'Lesson "{lesson.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete lesson: {str(e)}', 'danger')

    return redirect(url_for('course_detail', course_id=course_id))


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    """
    Serve uploaded files
    """
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# QUIZ ASSIGNMENTS

@app.route('/teacher/courses/<int:course_id>/quizzes/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_quiz(course_id):
    """
    Create a quiz for a course (teacher only)
    """
    course = Course.query.get_or_404(course_id)

    # Check if teacher owns the course
    if course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    modules = course.modules.order_by(Module.id).all()
    topics = Topic.query.join(Module).filter(Module.course_id == course_id).order_by(Topic.id).all()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        quiz_type = request.form.get('quiz_type', 'objective')
        time_limit = int(request.form.get('time_limit', 0) or 0)
        topic_id = request.form.get('topic_id') or None
        module_id = request.form.get('module_id') or None
        question_count = int(request.form.get('question_count', 0))

        if topic_id:
            topic_id = int(topic_id)
        if module_id:
            module_id = int(module_id)

        if not title:
            flash('Quiz title is required.', 'danger')
            return redirect(url_for('create_quiz', course_id=course_id))

        if topic_id and module_id:
            flash('Please choose either a related topic or a related module, not both.', 'danger')
            return redirect(url_for('create_quiz', course_id=course_id))

        if (modules or topics) and not (topic_id or module_id):
            flash('Please choose a related module or topic for the quiz.', 'danger')
            return redirect(url_for('create_quiz', course_id=course_id))

        try:
            quiz = Quiz(
                title=title,
                description=description,
                total_points=0,
                course_id=course_id,
                topic_id=topic_id,
                module_id=module_id,
                quiz_type=quiz_type,
                time_limit=time_limit
            )
            db.session.add(quiz)
            db.session.flush()  # Get quiz ID

            total_points = 0
            for i in range(question_count):
                question_text = request.form.get(f'question_{i}_text')
                points = int(request.form.get(f'question_{i}_points', 1) or 1)
                if not question_text:
                    continue

                if quiz_type == 'objective':
                    option_a = request.form.get(f'question_{i}_option_a')
                    option_b = request.form.get(f'question_{i}_option_b')
                    option_c = request.form.get(f'question_{i}_option_c')
                    option_d = request.form.get(f'question_{i}_option_d')
                    correct_option = request.form.get(f'question_{i}_correct')

                    if all([option_a, option_b, option_c, option_d, correct_option]):
                        question = QuizQuestion(
                            question_text=question_text,
                            question_type='objective',
                            option_a=option_a,
                            option_b=option_b,
                            option_c=option_c,
                            option_d=option_d,
                            correct_option=correct_option.upper(),
                            points=points,
                            quiz_id=quiz.id
                        )
                        db.session.add(question)
                        total_points += points
                elif quiz_type == 'qa':
                    question = QuizQuestion(
                        question_text=question_text,
                        question_type='qa',
                        points=points,
                        quiz_id=quiz.id
                    )
                    db.session.add(question)
                    total_points += points
                elif quiz_type == 'drawing':
                    question = QuizQuestion(
                        question_text=question_text,
                        question_type='drawing',
                        points=points,
                        quiz_id=quiz.id
                    )
                    db.session.add(question)
                    total_points += points

            if total_points == 0:
                flash('Please add at least one valid quiz question.', 'danger')
                return redirect(url_for('create_quiz', course_id=course_id))

            quiz.total_points = total_points
            db.session.commit()

            flash(f'Quiz "{title}" created successfully with {question_count} questions!', 'success')
            return redirect(url_for('course_detail', course_id=course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create quiz: {str(e)}', 'danger')
            return redirect(url_for('create_quiz', course_id=course_id))

    return render_template('assignments/create_quiz.html', course=course, modules=modules, topics=topics)


@app.route('/student/quizzes/<int:quiz_id>/take', methods=['GET', 'POST'])
@login_required
@student_required
def take_quiz(quiz_id):
    """
    Student takes a quiz
    Only enrolled students can take quizzes
    """
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if student is enrolled
    if not current_user.can_access_course(quiz.course_id):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('courses_list'))

    # Check if already submitted
    existing_submission = QuizSubmission.query.filter_by(
        student_id=current_user.id,
        quiz_id=quiz_id
    ).first()

    if existing_submission:
        flash('You have already submitted this quiz.', 'info')
        return redirect(url_for('course_detail', course_id=quiz.course_id))

    questions = quiz.questions.all()

    if request.method == 'POST':
        try:
            submission = QuizSubmission(
                student_id=current_user.id,
                quiz_id=quiz_id,
                total_score=0,
                graded=(quiz.quiz_type == 'objective')
            )

            db.session.add(submission)
            db.session.flush()  # Get submission ID

            total_score = 0

            for question in questions:
                if question.question_type == 'objective':
                    selected_option = request.form.get(f'question_{question.id}')
                    points_earned = 0
                    if selected_option and question.correct_option and selected_option.upper() == question.correct_option:
                        points_earned = question.points
                        total_score += points_earned
                    answer = QuizAnswer(
                        submission_id=submission.id,
                        question_id=question.id,
                        selected_option=selected_option.upper() if selected_option else None,
                        points_earned=points_earned
                    )
                    db.session.add(answer)
                elif question.question_type == 'qa':
                    text_answer = request.form.get(f'question_{question.id}_text', '').strip()
                    answer = QuizAnswer(
                        submission_id=submission.id,
                        question_id=question.id,
                        text_answer=text_answer
                    )
                    db.session.add(answer)
                elif question.question_type == 'drawing':
                    file = request.files.get(f'question_{question.id}_drawing')
                    drawing_path = None
                    if file and file.filename and allowed_file(file.filename):
                        filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file.filename}")
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_answers', filename)
                        os.makedirs(os.path.dirname(file_path), exist_ok=True)
                        file.save(file_path)
                        drawing_path = f'quiz_answers/{filename}'
                    else:
                        flash('Please upload a drawing image for every drawing question.', 'danger')
                        return redirect(url_for('take_quiz', quiz_id=quiz_id))

                    answer = QuizAnswer(
                        submission_id=submission.id,
                        question_id=question.id,
                        drawing_path=drawing_path
                    )
                    db.session.add(answer)

            submission.total_score = total_score
            if submission.graded:
                submission.graded_at = datetime.utcnow()

            db.session.commit()

            if quiz.quiz_type == 'objective':
                percentage = calculate_grade_percentage(total_score, quiz.total_points)
                flash(f'Quiz submitted! Your score: {total_score}/{quiz.total_points} ({percentage}%)', 'success')
            else:
                flash('Quiz submitted! Your answers have been recorded and will be reviewed by your teacher.', 'success')

            return redirect(url_for('course_detail', course_id=quiz.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to submit quiz: {str(e)}', 'danger')
            return redirect(url_for('take_quiz', quiz_id=quiz_id))

    return render_template('assignments/take_quiz.html', quiz=quiz, questions=questions)


@app.route('/teacher/quizzes/<int:quiz_id>/submissions')
@login_required
@teacher_required
def quiz_submissions(quiz_id):
    """
    View all quiz submissions (teacher only)
    """
    quiz = Quiz.query.get_or_404(quiz_id)

    # Check if teacher owns the course
    if quiz.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    submissions = quiz.submissions.order_by(QuizSubmission.submitted_at.desc()).all()

    return render_template('assignments/quiz_submissions.html', quiz=quiz, submissions=submissions)


@app.route('/teacher/quizzes/<int:quiz_id>/submissions/<int:submission_id>/grade', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_quiz_submission(quiz_id, submission_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    submission = QuizSubmission.query.filter_by(id=submission_id, quiz_id=quiz_id).first_or_404()
    answers = submission.answers.all()

    if request.method == 'POST':
        try:
            total_score = 0
            for answer in answers:
                question = answer.question

                feedback = request.form.get(f'answer_{answer.id}_feedback', '').strip()
                answer.teacher_feedback = feedback if feedback else None

                if question.question_type == 'objective':
                    total_score += answer.points_earned
                else:
                    points = int(request.form.get(f'answer_{answer.id}_score', 0) or 0)
                    answer.points_earned = max(0, min(points, question.points))
                    total_score += answer.points_earned

            submission.total_score = total_score
            submission.graded = True
            submission.graded_at = datetime.utcnow()
            db.session.commit()

            flash('Quiz submission graded successfully.', 'success')
            return redirect(url_for('quiz_submissions', quiz_id=quiz_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Unable to grade submission: {str(e)}', 'danger')
            return redirect(url_for('grade_quiz_submission', quiz_id=quiz_id, submission_id=submission_id))

    return render_template('assignments/grade_quiz.html', quiz=quiz, submission=submission, answers=answers)


@app.route('/courses/<int:course_id>/discussions')
@login_required
def course_discussions(course_id):
    course = Course.query.get_or_404(course_id)

    if current_user.is_student and not current_user.can_access_course(course_id):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('courses_list'))

    search = request.args.get('search', '').strip()
    discussion_query = Discussion.query.filter_by(course_id=course_id)

    if search:
        ilike_pattern = f"%{search}%"
        discussion_query = discussion_query.filter(
            or_(
                Discussion.title.ilike(ilike_pattern),
                Discussion.content.ilike(ilike_pattern)
            )
        )

    discussions = discussion_query.order_by(Discussion.is_pinned.desc(), Discussion.created_at.desc()).all()

    return render_template('discussions/list.html', course=course, discussions=discussions, search=search)


@app.route('/teacher/quizzes/<int:quiz_id>/leaderboard')
@login_required
@teacher_required
def quiz_leaderboard(quiz_id):
    """Show leaderboard for a quiz based on points earned"""
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    leaderboard = quiz.submissions.filter_by(graded=True).order_by(QuizSubmission.total_score.desc(), QuizSubmission.submitted_at.asc()).all()
    return render_template('assignments/quiz_leaderboard.html', quiz=quiz, leaderboard=leaderboard)


# ESSAY ASSIGNMENTS

@app.route('/teacher/courses/<int:course_id>/essays/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def create_essay(course_id):
    """
    Create an essay assignment for a course (teacher only)
    Supports text-based or file-based submissions
    """
    course = Course.query.get_or_404(course_id)

    # Check if teacher owns the course
    if course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        question_text = request.form.get('question_text')
        allows_file_upload = request.form.get('allows_file_upload') == 'on'
        max_points = request.form.get('max_points', 100)
        due_date_str = request.form.get('due_date')

        if not title or not question_text:
            flash('Essay title and question are required.', 'danger')
            return redirect(url_for('create_essay', course_id=course_id))

        try:
            essay = Essay(
                title=title,
                question_text=question_text,
                allows_file_upload=allows_file_upload,
                max_points=int(max_points),
                due_date=datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None,
                course_id=course_id
            )

            db.session.add(essay)
            db.session.commit()

            flash(f'Essay assignment "{title}" created successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create essay: {str(e)}', 'danger')
            return redirect(url_for('create_essay', course_id=course_id))

    return render_template('assignments/create_essay.html', course=course)


@app.route('/student/essays/<int:essay_id>/submit', methods=['GET', 'POST'])
@login_required
@student_required
def submit_essay(essay_id):
    """
    Student submits an essay
    Text-based or file-based
    """
    essay = Essay.query.get_or_404(essay_id)

    # Check if student is enrolled
    if not current_user.can_access_course(essay.course_id):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('courses_list'))

    # Check if already submitted
    existing_submission = EssaySubmission.query.filter_by(
        student_id=current_user.id,
        essay_id=essay_id
    ).first()

    if existing_submission:
        flash('You have already submitted this essay.', 'info')
        return redirect(url_for('course_detail', course_id=essay.course_id))

    if request.method == 'POST':
        text_content = request.form.get('text_content')

        # Handle file upload
        uploaded_file = None
        if essay.allows_file_upload and 'uploaded_file' in request.files:
            file_upload = request.files['uploaded_file']
            if file_upload.filename and allowed_file(file_upload.filename):
                filename = secure_filename(f"{datetime.utcnow().timestamp()}_{file_upload.filename}")
                file_upload.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                uploaded_file = filename

        if not text_content and not uploaded_file:
            flash('Please provide text content or upload a file.', 'danger')
            return redirect(url_for('submit_essay', essay_id=essay_id))

        try:
            submission = EssaySubmission(
                student_id=current_user.id,
                essay_id=essay_id,
                text_content=text_content,
                uploaded_file=uploaded_file
            )

            db.session.add(submission)
            db.session.commit()

            flash('Essay submitted successfully!', 'success')
            return redirect(url_for('course_detail', course_id=essay.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to submit essay: {str(e)}', 'danger')
            return redirect(url_for('submit_essay', essay_id=essay_id))

    return render_template('assignments/submit_essay.html', essay=essay)


@app.route('/teacher/essays/<int:essay_id>/submissions')
@login_required
@teacher_required
def essay_submissions(essay_id):
    """
    View all essay submissions (teacher only)
    """
    essay = Essay.query.get_or_404(essay_id)

    # Check if teacher owns the course
    if essay.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    submissions = essay.submissions.order_by(EssaySubmission.submitted_at.desc()).all()

    return render_template('assignments/essay_submissions.html', essay=essay, submissions=submissions)


@app.route('/teacher/essay-submissions/<int:submission_id>/grade', methods=['GET', 'POST'])
@login_required
@teacher_required
def grade_essay_submission(submission_id):
    """
    Grade an essay submission (teacher only)
    """
    submission = EssaySubmission.query.get_or_404(submission_id)

    # Check if teacher owns the course
    if submission.essay.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        score = request.form.get('score')
        feedback = request.form.get('feedback')

        if not score:
            flash('Score is required.', 'danger')
            return redirect(url_for('grade_essay_submission', submission_id=submission_id))

        try:
            submission.score = int(score)
            submission.feedback = feedback
            submission.graded = True
            submission.graded_at = datetime.utcnow()

            db.session.commit()

            flash(f'Essay graded successfully!', 'success')
            return redirect(url_for('essay_submissions', essay_id=submission.essay_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to grade essay: {str(e)}', 'danger')
            return redirect(url_for('grade_essay_submission', submission_id=submission_id))

    return render_template('assignments/grade_essay.html', submission=submission)


# GRADING SYSTEM

@app.route('/student/grades')
@login_required
@student_required
def student_grades():
    """
    Student grade dashboard
    Shows quiz and essay grades for all enrolled courses
    """
    # Get quiz submissions
    quiz_submissions = QuizSubmission.query.filter_by(
        student_id=current_user.id
    ).order_by(QuizSubmission.submitted_at.desc()).all()

    # Get essay submissions
    essay_submissions = EssaySubmission.query.filter_by(
        student_id=current_user.id
    ).order_by(EssaySubmission.submitted_at.desc()).all()

    graded_quiz_submissions = [s for s in quiz_submissions if s.graded]

    # Calculate overall statistics using only graded quiz submissions
    total_quiz_score = sum([s.total_score for s in graded_quiz_submissions])
    total_quiz_points = sum([s.quiz.total_points for s in graded_quiz_submissions])
    quiz_percentage = calculate_grade_percentage(total_quiz_score, total_quiz_points)

    graded_essays = [s for s in essay_submissions if s.graded]
    total_essay_score = sum([s.score for s in graded_essays])
    total_essay_points = sum([s.essay.max_points for s in graded_essays])
    essay_percentage = calculate_grade_percentage(total_essay_score, total_essay_points)

    return render_template('student/grades.html',
                           quiz_submissions=quiz_submissions,
                           essay_submissions=essay_submissions,
                           quiz_percentage=quiz_percentage,
                           essay_percentage=essay_percentage)


@app.route('/student/quizzes/submissions/<int:submission_id>')
@login_required
@student_required
def student_quiz_review(submission_id):
    submission = QuizSubmission.query.get_or_404(submission_id)
    if submission.student_id != current_user.id:
        flash('Access denied. You may only view your own quiz reviews.', 'danger')
        return redirect(url_for('student_grades'))

    return render_template('student/quiz_review.html', submission=submission)


# LIVE BIOLOGY CLASSES

@app.route('/teacher/courses/<int:course_id>/live-class/start', methods=['GET', 'POST'])
@login_required
@teacher_required
def start_live_class(course_id):
    """
    Start a live class (teacher only)
    Only one active class per course
    """
    course = Course.query.get_or_404(course_id)

    # Check if teacher owns the course
    if course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    # Check if there's already an active live class
    active_class = LiveClass.query.filter_by(
        course_id=course_id,
        is_active=True
    ).first()

    if active_class:
        flash(f'There is already an active live class: "{active_class.title}"', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        stream_url = request.form.get('stream_url')

        if not title or not stream_url:
            flash('Title and stream URL are required.', 'danger')
            return redirect(url_for('start_live_class', course_id=course_id))

        try:
            live_class = LiveClass(
                title=title,
                description=description,
                stream_url=stream_url,
                is_active=True,
                started_at=datetime.utcnow(),
                course_id=course_id
            )

            db.session.add(live_class)
            db.session.commit()

            flash(f'Live class "{title}" started successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to start live class: {str(e)}', 'danger')
            return redirect(url_for('start_live_class', course_id=course_id))

    return render_template('live/start_live_class.html', course=course)


@app.route('/teacher/live-classes/<int:live_class_id>/end', methods=['POST'])
@login_required
@teacher_required
def end_live_class(live_class_id):
    """
    End a live class (teacher only)
    """
    live_class = LiveClass.query.get_or_404(live_class_id)

    # Check if teacher owns the course
    if live_class.course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    try:
        live_class.is_active = False
        live_class.ended_at = datetime.utcnow()
        db.session.commit()

        flash(f'Live class "{live_class.title}" ended successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to end live class: {str(e)}', 'danger')

    return redirect(url_for('course_detail', course_id=live_class.course_id))


# DISCUSSIONS

@app.route('/courses/<int:course_id>/discussions/create', methods=['GET', 'POST'])
@login_required
def create_discussion(course_id):
    """
    Create a discussion (teachers and enrolled students)
    """
    course = Course.query.get_or_404(course_id)

    # Check access
    if current_user.is_student and not current_user.can_access_course(course_id):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        is_pinned = request.form.get('is_pinned') == 'on'

        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('create_discussion', course_id=course_id))

        try:
            discussion = Discussion(
                title=title,
                content=content,
                is_pinned=is_pinned and current_user.is_teacher,
                course_id=course_id,
                author_id=current_user.id
            )

            db.session.add(discussion)
            db.session.commit()

            flash(f'Discussion "{title}" created successfully!', 'success')
            return redirect(url_for('course_discussions', course_id=course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create discussion: {str(e)}', 'danger')
            return redirect(url_for('create_discussion', course_id=course_id))

    return render_template('discussions/create.html', course=course)


@app.route('/discussions/<int:discussion_id>/reply', methods=['GET', 'POST'])
@login_required
def reply_discussion(discussion_id):
    """
    Reply to a discussion (teachers and enrolled students)
    """
    discussion = Discussion.query.get_or_404(discussion_id)

    # Check access
    if current_user.is_student and not current_user.can_access_course(discussion.course_id):
        flash('You are not enrolled in this course.', 'warning')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        content = request.form.get('content')

        if not content:
            flash('Reply content is required.', 'danger')
            return redirect(url_for('reply_discussion', discussion_id=discussion_id))

        try:
            reply = Reply(
                content=content,
                discussion_id=discussion_id,
                author_id=current_user.id
            )

            db.session.add(reply)
            db.session.commit()

            flash('Reply posted successfully!', 'success')
            return redirect(url_for('course_discussions', course_id=discussion.course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to post reply: {str(e)}', 'danger')
            return redirect(url_for('reply_discussion', discussion_id=discussion_id))

    return render_template('discussions/reply.html', discussion=discussion)


# NOTIFICATIONS

@app.route('/admin/notifications/create', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_create_notification():
    """
    Create a notification (admin only)
    Can send to all students or specific student
    """
    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')
        recipient_id = request.form.get('recipient_id')

        if not title or not message:
            flash('Title and message are required.', 'danger')
            return redirect(url_for('admin_create_notification'))

        try:
            # If recipient_id is 'all', send to all students
            if recipient_id == 'all':
                students = User.query.filter_by(user_type='student').all()
                for student in students:
                    notification = Notification(
                        title=title,
                        message=message,
                        recipient_id=student.id
                    )
                    db.session.add(notification)
            else:
                # Send to specific student
                notification = Notification(
                    title=title,
                    message=message,
                    recipient_id=int(recipient_id)
                )
                db.session.add(notification)

            db.session.commit()

            flash('Notification(s) sent successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to send notification: {str(e)}', 'danger')
            return redirect(url_for('admin_create_notification'))

    # Get all students for dropdown
    students = User.query.filter_by(user_type='student').all()

    return render_template('admin/create_notification.html', students=students)


@app.route('/admin/teachers/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_teacher():
    """
    Create a new teacher account (admin only)
    """
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date_of_birth = request.form.get('date_of_birth')

        # Validation
        if not all([username, password, first_name, last_name, date_of_birth]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('create_teacher'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('create_teacher'))

        if User.query.filter_by(username=username).first():
            flash('Email already registered. Please use a different email.', 'danger')
            return redirect(url_for('create_teacher'))

        try:
            # Create new teacher
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=datetime.strptime(date_of_birth, '%Y-%m-%d'),
                user_type='teacher'
            )
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            flash(f'Teacher account created successfully for {first_name} {last_name}!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to create teacher account: {str(e)}', 'danger')
            return redirect(url_for('create_teacher'))

    return render_template('admin/create_teacher.html')


@app.route('/teacher/courses/<int:course_id>/notifications/create', methods=['GET', 'POST'])
@login_required
@teacher_required
def teacher_create_notification(course_id):
    """
    Create a notification for course students (teacher only)
    """
    course = Course.query.get_or_404(course_id)

    # Check if teacher owns the course
    if course.teacher_id != current_user.id:
        flash('Access denied. You do not own this course.', 'danger')
        return redirect(url_for('courses_list'))

    if request.method == 'POST':
        title = request.form.get('title')
        message = request.form.get('message')

        if not title or not message:
            flash('Title and message are required.', 'danger')
            return redirect(url_for('teacher_create_notification', course_id=course_id))

        try:
            # Get enrolled students
            enrollments = Enrollment.query.filter_by(
                course_id=course_id,
                status='approved'
            ).all()

            for enrollment in enrollments:
                notification = Notification(
                    title=title,
                    message=message,
                    recipient_id=enrollment.student_id
                )
                db.session.add(notification)

            db.session.commit()

            flash(f'Notification sent to {len(enrollments)} students successfully!', 'success')
            return redirect(url_for('course_detail', course_id=course_id))

        except Exception as e:
            db.session.rollback()
            flash(f'Failed to send notification: {str(e)}', 'danger')
            return redirect(url_for('teacher_create_notification', course_id=course_id))

    return render_template('teacher/create_notification.html', course=course)


@app.route('/student/notifications')
@login_required
@student_required
def student_notifications():
    """
    View all notifications for current student
    """
    notifications = Notification.query.filter_by(
        recipient_id=current_user.id
    ).order_by(Notification.created_at.desc()).all()

    return render_template('student/notifications.html', notifications=notifications)


@app.route('/student/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
@student_required
def mark_notification_read(notification_id):
    """
    Mark notification as read
    """
    notification = Notification.query.get_or_404(notification_id)

    if notification.recipient_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('student_notifications'))

    try:
        notification.read_at = datetime.utcnow()
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    return redirect(url_for('student_notifications'))


# DIGITAL BIOLOGY LIBRARY

# Wikipedia helper function
def wikipedia_summary(query):
    for variant in [query, query.title()]:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{variant.replace(' ', '_')}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "extract" in data and data["extract"].strip():
                    return data["extract"]
        except Exception:
            continue
    return None



# Assuming you have your wikipedia fallback helper function imported or defined:
# from utils import wikipedia_summary 

@app.route('/library/ai-research', methods=['POST'])
@login_required
def library_ai_research():
    """
    AI Pool Research Endpoint
    Routes queries through the multi-account Gemini key array with dynamic 
    E-Library database catalog integration and Wikipedia fallback protection.
    """
    payload = request.get_json(silent=True) or {}
    query = str(payload.get('query', '')).strip()
    if not query:
        return jsonify({'response': 'Please enter a topic.', 'source': None, 'success': False}), 400

    try:
        # 1. Fetch available resources from your exact database model
        all_resources = LibraryResource.query.all()
        
        # 2. Compile database records into a clean catalog layout for Gemini context
        catalog_items = []
        for res in all_resources:
            title = str(res.title).replace('\n', ' ').strip()
            desc = str(res.description).replace('\n', ' ').strip() if res.description else "No overview detailed."
            cat = str(res.category).replace('\n', ' ').strip() if res.category else "General Biology"
            author_str = f" by {res.author}" if res.author else ""
            
            catalog_items.append(f"- [{cat}] '{title}'{author_str}: {desc}")
            
        if catalog_items:
            catalog_context = "\n".join(catalog_items)
        else:
            catalog_context = "There are currently no books or materials uploaded to the library resource database."

        # 3. Query the intelligent multi-account token manager using pool rotation
        response, source_model, success = ai_pool.answer_question(query, catalog_context=catalog_context)
        
        if success and response:
            # Clean up response string wrapper quotes if present
            response = response.strip()
            if response.startswith('"'):
                response = response[1:]
            if response.endswith('"'):
                response = response[:-1]
            
            return jsonify({
                'response': response,
                'source': source_model or 'The Eagle AI',
                'model': ai_pool.settings.get("gemini_model", "gemini-2.5-flash-lite"),
                'success': True
            }), 200

    except Exception as e:
        print(f"Internal processing exception caught on library research node: {str(e)}")
        # Don't crash out immediately; let it fall through to Wikipedia if a db issue occurs
    
    # 4. Fallback to Wikipedia summary if all account keys are exhausted or down
    try:
        wiki_response = wikipedia_summary(query)
        if wiki_response:
            return jsonify({
                'response': wiki_response.strip(),
                'source': 'Wikipedia',
                'success': True
            }), 200
    except Exception as wiki_err:
        print(f"Wikipedia fallback failed: {str(wiki_err)}")
    
    # 5. Total system exhaustion escape handler
    return jsonify({
        'response': 'Unable to find an answer. Try a more general biology term.',
        'source': None,
        'success': False,
        'error': getattr(ai_pool, 'last_error', 'All configured account quotas are exhausted.')
    }), 500

@app.route('/admin/ai-pool/status', methods=['GET'])
@login_required
@admin_required
def ai_pool_status():
    """
    View AI Pool status (admin only)
    Shows token usage, available models, and cache info
    """
    status = ai_pool.get_pool_status()
    cache_size = len(ai_pool.model_cache)
    
    available_count = sum(1 for s in status if s['available'])
    total_requests = sum(s['requests_used'] for s in status)
    
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'available_models': available_count,
        'total_models': len(status),
        'total_requests': total_requests,
        'cache_size': cache_size,
        'models': status
    }), 200

@app.route('/admin/ai-pool/reset', methods=['POST'])
@login_required
@admin_required
def reset_ai_pool():
    """
    Manually reset AI Pool (admin only)
    Resets all token counters
    """
    ai_pool.reset_pool()
    flash('AI Pool has been reset. All token counters cleared.', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/ai-pool/validate', methods=['POST'])
@login_required
@admin_required
def validate_ai_pool():
    """
    Validate all configured Hugging Face models (admin only)
    """
    results = ai_pool.validate_huggingface_models()
    passed = sum(1 for r in results if r["ok"])
    failed = len(results) - passed
    return jsonify({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed_models": passed,
        "failed_models": failed,
        "total_models": len(results),
        "results": results,
    }), 200


@app.route('/library')
@login_required
def library_index():
    """
    View digital library
    Search and filter resources
    """
    # Get search parameters
    search = request.args.get('search', '')
    category = request.args.get('category', '')

    # Build query
    query = LibraryResource.query

    if search:
        query = query.filter(
            (LibraryResource.title.contains(search)) |
            (LibraryResource.description.contains(search)) |
            (LibraryResource.tags.contains(search))
        )

    if category:
        query = query.filter_by(category=category)

    resources = query.order_by(LibraryResource.uploaded_at.desc()).all()

    # Get unique categories
    categories = db.session.query(LibraryResource.category).distinct().all()
    categories = [c[0] for c in categories if c[0]]

    return render_template('library/index.html',
                           resources=resources,
                           categories=categories,
                           search=search,
                           category=category)


@app.route('/admin/library/upload', methods=['GET', 'POST'])
@login_required
@admin_required
def upload_library_resource():
    """
    Upload a resource to digital library (admin only)
    """
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        author = request.form.get('author')
        tags = request.form.get('tags')

        if 'file' in request.files:
            file_upload = request.files['file']
            if file_upload.filename and allowed_file(file_upload.filename):
                filename = secure_filename(f"{datetime.now(timezone.utc).timestamp()}_{file_upload.filename}")
                file_upload.save(os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files', filename))

                # Determine category
                category = filename.rsplit('.', 1)[1].upper()

                try:
                    resource = LibraryResource(
                        title=title,
                        description=description,
                        author=author,
                        tags=tags,
                        category=category,
                        file_name=filename,
                        file_size=os.path.getsize(os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files', filename))
                    )

                    db.session.add(resource)
                    db.session.commit()

                    flash(f'Resource "{title}" uploaded successfully!', 'success')
                    return redirect(url_for('library_index'))

                except Exception as e:
                    db.session.rollback()
                    flash(f'Failed to upload resource: {str(e)}', 'danger')
                    return redirect(url_for('upload_library_resource'))
            else:
                flash('Invalid file type or no file selected.', 'danger')
                return redirect(url_for('upload_library_resource'))
        else:
            flash('No file selected.', 'danger')
            return redirect(url_for('upload_library_resource'))

    return render_template('library/upload.html')

@app.route('/admin/library/bulk-upload', methods=['GET', 'POST'])
@login_required
@admin_required
def bulk_upload_library_resources():
    """
    Bulk upload multiple resources to digital library (admin only)
    """
    if request.method == 'POST':
        uploaded_count = 0
        failed_count = 0
        errors = []
        
        # Get common metadata
        common_author = request.form.get('common_author', '')
        common_tags = request.form.get('common_tags', '')
        
        # Get files
        files = request.files.getlist('files')
        
        if not files or files[0].filename == '':
            flash('No files selected.', 'danger')
            return redirect(url_for('bulk_upload_library_resources'))
        
        for file_upload in files:
            try:
                if file_upload.filename and allowed_file(file_upload.filename):
                    filename = secure_filename(f"{datetime.now(timezone.utc).timestamp()}_{file_upload.filename}")
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files', filename)
                    file_upload.save(file_path)
                    
                    # Determine category from extension
                    category = filename.rsplit('.', 1)[1].upper()
                    
                    # Create resource with auto-generated title if not provided
                    title = request.form.get(f'title_{uploaded_count}', file_upload.filename.rsplit('.', 1)[0])
                    description = request.form.get(f'description_{uploaded_count}', '')
                    author = request.form.get(f'author_{uploaded_count}', common_author)
                    tags = request.form.get(f'tags_{uploaded_count}', common_tags)
                    
                    resource = LibraryResource(
                        title=title,
                        description=description,
                        author=author,
                        tags=tags,
                        category=category,
                        file_name=filename,
                        file_size=os.path.getsize(file_path)
                    )
                    
                    db.session.add(resource)
                    uploaded_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Invalid file: {file_upload.filename}")
            
            except Exception as e:
                failed_count += 1
                errors.append(f"Error uploading {file_upload.filename}: {str(e)}")
        
        try:
            db.session.commit()
            flash(f'Successfully uploaded {uploaded_count} resources!', 'success')
            if errors:
                for error in errors:
                    flash(error, 'warning')
            return redirect(url_for('library_index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to save resources: {str(e)}', 'danger')
            return redirect(url_for('bulk_upload_library_resources'))
    
    return render_template('library/upload.html')

# ================================
# STUDENT QUESTION & TEACHER ANSWER ROUTES
# ================================

@app.route('/student/ask', methods=['GET', 'POST'])
@login_required
def ask_question():
    """
    Student asking a question to all teachers
    """
    if current_user.user_type != 'student':
        flash('Only students can ask questions.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        question_type = request.form.get('question_type', 'text')
        attachment_path = None
        
        # Handle file upload (image or voice)
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now(timezone.utc).timestamp()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'questions', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                attachment_path = f'questions/{filename}'
                extension = filename.rsplit('.', 1)[-1].lower()
                if extension in {'jpg', 'jpeg', 'png', 'gif'}:
                    question_type = 'image'
                elif extension in {'mp3', 'wav', 'webm', 'ogg', 'm4a'}:
                    question_type = 'voice'
            elif file and file.filename:
                flash('Attachment file type is not supported.', 'danger')
                return redirect(url_for('ask_question'))
        
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return redirect(url_for('ask_question'))
        
        try:
            question = StudentQuestion(
                title=title,
                content=content,
                question_type=question_type,
                attachment_path=attachment_path,
                student_id=current_user.id
            )
            
            db.session.add(question)
            db.session.commit()
            
            # Send notifications to all teachers
            teachers = User.query.filter_by(user_type='teacher').all()
            for teacher in teachers:
                notification = Notification(
                    title=f'New Question from {current_user.full_name}',
                    message=f'"{title}"',
                    recipient_id=teacher.id
                )
                db.session.add(notification)
            
            db.session.commit()
            flash('Question posted! All teachers have been notified.', 'success')
            return redirect(url_for('student_questions'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error posting question: {str(e)}', 'danger')
            return redirect(url_for('ask_question'))
    
    return render_template('student/ask_question.html')

@app.route('/student/questions')
@login_required
def student_questions():
    """
    View student's questions and answers
    """
    if current_user.user_type != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    questions = StudentQuestion.query.filter_by(student_id=current_user.id) \
        .order_by(StudentQuestion.created_at.desc()) \
        .paginate(page=page, per_page=10)
    
    return render_template('student/questions_inbox.html', questions=questions)

@app.route('/student/question/<int:question_id>')
@login_required
def view_question_answers(question_id):
    """
    View a specific question and all teacher answers
    """
    question = StudentQuestion.query.get_or_404(question_id)
    
    if question.student_id != current_user.id and current_user.user_type != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('student_questions'))
    
    answers = TeacherAnswer.query.filter_by(question_id=question_id) \
        .order_by(TeacherAnswer.created_at.desc()).all()
    
    return render_template('student/view_answers.html', question=question, answers=answers)

@app.route('/teacher/questions-inbox')
@login_required
def teacher_questions_inbox():
    """
    View questions from students (teacher inbox)
    """
    if current_user.user_type != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    page = request.args.get('page', 1, type=int)
    questions = StudentQuestion.query \
        .order_by(StudentQuestion.created_at.desc()) \
        .paginate(page=page, per_page=10)
    
    return render_template('teacher/questions_inbox.html', questions=questions)

@app.route('/teacher/question/<int:question_id>/answer', methods=['GET', 'POST'])
@login_required
def answer_question(question_id):
    """
    Teacher answering a student question
    """
    if current_user.user_type != 'teacher':
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))
    
    question = StudentQuestion.query.get_or_404(question_id)
    
    if request.method == 'POST':
        content = request.form.get('content')
        answer_type = request.form.get('answer_type', 'text')
        attachment_path = None
        
        # Handle file upload (image or voice)
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(f"{datetime.now(timezone.utc).timestamp()}_{file.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'answers', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                attachment_path = f'answers/{filename}'
        
        if not content:
            flash('Answer content is required.', 'danger')
            return redirect(url_for('answer_question', question_id=question_id))
        
        try:
            # Check if teacher already answered this question
            existing_answer = TeacherAnswer.query.filter_by(
                question_id=question_id,
                teacher_id=current_user.id
            ).first()
            
            if existing_answer:
                # Update existing answer
                existing_answer.content = content
                existing_answer.answer_type = answer_type
                existing_answer.attachment_path = attachment_path
                existing_answer.created_at = datetime.now(timezone.utc)
                db.session.commit()
                flash('Answer updated!', 'success')
            else:
                # Create new answer
                answer = TeacherAnswer(
                    content=content,
                    answer_type=answer_type,
                    attachment_path=attachment_path,
                    question_id=question_id,
                    teacher_id=current_user.id
                )
                
                db.session.add(answer)
                db.session.commit()
                
                # Send notification to student
                notification = Notification(
                    title=f'{current_user.full_name} answered your question',
                    message=f'"{question.title}"',
                    recipient_id=question.student_id
                )
                db.session.add(notification)
                db.session.commit()
                
                flash('Answer posted! Student has been notified.', 'success')
            
            return redirect(url_for('teacher_questions_inbox'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Error posting answer: {str(e)}', 'danger')
            return redirect(url_for('answer_question', question_id=question_id))
    
    # Check if teacher already answered
    existing_answer = TeacherAnswer.query.filter_by(
        question_id=question_id,
        teacher_id=current_user.id
    ).first()
    
    return render_template('teacher/answer_question.html', question=question, existing_answer=existing_answer)

# LESSON VIEW ROUTE
# Add this in app.py, preferably near the other lesson routes

# In app.py

@app.route('/lessons/<int:lesson_id>')
@login_required
def view_lesson(lesson_id):
    """
    View a specific lesson in a dedicated learning interface
    """
    lesson = Lesson.query.get_or_404(lesson_id)
    course = lesson.topic.module.course

    # Access Control
    if current_user.is_student:
        if not current_user.can_access_course(course.id):
            flash('You are not enrolled in this course.', 'warning')
            return redirect(url_for('courses_list'))
    elif current_user.is_teacher:
        if course.teacher_id != current_user.id:
            flash('You do not teach this course.', 'danger')
            return redirect(url_for('dashboard'))

    # Get curriculum data for sidebar
    modules = Module.query.filter_by(course_id=course.id).order_by(Module.order).all()

    # CRITICAL: Ensure this path matches your new structure
    return render_template('lessons/view_lesson.html',
                           lesson=lesson,
                           course=course,
                           modules=modules)
@app.route('/library/<int:resource_id>/view')
@login_required
def view_library_resource(resource_id):
    """
    View a library resource (Strictly View-Only)
    Disables download and uses an iframe/embed viewer.
    """
    resource = LibraryResource.query.get_or_404(resource_id)
    preview_token = build_preview_token(resource.id, current_user.id)
    if resource.file_extension == 'pdf':
        return render_template('library/view_pdf.html', resource=resource, preview_token=preview_token)
    return render_template('library/viewer.html', resource=resource, preview_token=preview_token)


from flask import send_from_directory, abort, make_response
from werkzeug.utils import secure_filename
import os

@app.route('/library/files/<filename>')
@login_required
def serve_library_file(filename):
    directory = os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files')
    secure_name = secure_filename(filename)

    if not os.path.exists(os.path.join(directory, secure_name)):
        # Legacy fallback to older library storage location
        legacy_directory = os.path.join(app.config['UPLOAD_FOLDER'], 'library')
        if os.path.exists(os.path.join(legacy_directory, secure_name)):
            directory = legacy_directory
        else:
            abort(404)

    mime_types = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'svg': 'image/svg+xml'
    }

    ext = secure_name.rsplit('.', 1)[-1].lower()
    resource = LibraryResource.query.filter_by(file_name=secure_name).first_or_404()
    preview_token = request.args.get('token', '')
    if not validate_preview_token(preview_token, resource.id, current_user.id):
        abort(403)

    mimetype = mime_types.get(ext, 'application/octet-stream')

    response = send_from_directory(
        directory,
        secure_name,
        mimetype=mimetype,
        as_attachment=False,
        conditional=True
    )

    # Keep files embeddable for in-site preview only.
    if ext == 'pdf':
        response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename="{secure_name}"'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Accept-Ranges'] = 'bytes'
    response.headers['Cache-Control'] = 'private, no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response


@app.route('/library/download/<int:resource_id>')
@login_required
def download_library_resource(resource_id):
    abort(403)


@app.route('/admin/library/<int:resource_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_library_resource(resource_id):
    """
    Edit a library resource (admin only)
    """
    resource = LibraryResource.query.get_or_404(resource_id)

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        author = request.form.get('author')
        tags = request.form.get('tags')

        resource.title = title or resource.title
        resource.description = description
        resource.author = author
        resource.tags = tags

        if 'file' in request.files:
            file_upload = request.files['file']
            if file_upload and file_upload.filename and allowed_file(file_upload.filename):
                filename = secure_filename(f"{datetime.now(timezone.utc).timestamp()}_{file_upload.filename}")
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files', filename)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file_upload.save(file_path)

                # Remove old file if it exists
                old_file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files', resource.file_name)
                legacy_old_path = os.path.join(app.config['UPLOAD_FOLDER'], 'library', resource.file_name)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                elif os.path.exists(legacy_old_path):
                    os.remove(legacy_old_path)

                resource.file_name = filename
                resource.category = filename.rsplit('.', 1)[1].upper()
                resource.file_size = os.path.getsize(file_path)

        try:
            db.session.commit()
            flash(f'Resource "{resource.title}" updated successfully!', 'success')
            return redirect(url_for('library_index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Failed to update resource: {str(e)}', 'danger')
            return redirect(url_for('edit_library_resource', resource_id=resource_id))

    return render_template('library/edit.html', resource=resource)


@app.route('/admin/library/<int:resource_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_library_resource(resource_id):
    """
    Delete a library resource (admin only)
    """
    resource = LibraryResource.query.get_or_404(resource_id)

    try:
        # Delete file
        library_directory = os.path.join(app.config['UPLOAD_FOLDER'], 'library', 'files')
        legacy_directory = os.path.join(app.config['UPLOAD_FOLDER'], 'library')
        file_path = os.path.join(library_directory, resource.file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            legacy_path = os.path.join(legacy_directory, resource.file_name)
            if os.path.exists(legacy_path):
                os.remove(legacy_path)

        # Delete database record
        db.session.delete(resource)
        db.session.commit()

        flash(f'Resource "{resource.title}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete resource: {str(e)}', 'danger')

    return redirect(url_for('library_index'))


# ERROR HANDLERS

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return render_template('errors/500.html'), 500


# DATABASE INITIALIZATION & RUN

def upgrade_database_schema():
    """Ensure database schema matches the current SQLAlchemy models."""
    try:
        inspector = inspect(db.engine)
        if 'quizzes' in inspector.get_table_names():
            columns = {column['name'] for column in inspector.get_columns('quizzes')}
            if 'quiz_type' not in columns:
                print("Adding quiz_type column to quizzes...")
                db.session.execute(text("ALTER TABLE quizzes ADD COLUMN quiz_type VARCHAR(20) DEFAULT 'objective'"))
            if 'time_limit' not in columns:
                print("Adding time_limit column to quizzes...")
                db.session.execute(text('ALTER TABLE quizzes ADD COLUMN time_limit INTEGER DEFAULT 0'))
        if 'quiz_answers' in inspector.get_table_names():
            columns = {column['name'] for column in inspector.get_columns('quiz_answers')}
            if 'teacher_feedback' not in columns:
                print("Adding teacher_feedback column to quiz_answers...")
                db.session.execute(text('ALTER TABLE quiz_answers ADD COLUMN teacher_feedback TEXT'))
        db.session.commit()
        print("Database schema upgrade completed.")
    except Exception as e:
        print(f"Database schema upgrade error: {e}")
        db.session.rollback()


def initialize_database():
    """Create tables and upgrade schema once at startup."""
    if not hasattr(app, '_database_initialized'):
        db.create_all()
        upgrade_database_schema()
        app._database_initialized = True


@app.before_request
def create_tables():
    """Create database tables if they don't exist"""
    if not hasattr(app, '_schema_upgraded'):
        try:
            upgrade_database_schema()
            app._schema_upgraded = True
        except Exception as e:
            print(f"Schema upgrade warning: {e}")


if __name__ == '__main__':
    with app.app_context():
        print("Initializing database...")
        initialize_database()
    print("Starting Flask app...")
    app.run(debug=app.config.get('DEBUG', False), host='0.0.0.0', port=5000)
