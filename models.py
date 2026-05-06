"""
Database Models for The Eagle Biology Class LMS
"""
from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ================================
# USER MODEL
# ================================

class User(UserMixin, db.Model):
    """User model for authentication and role-based access"""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)  # Email
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # 'admin', 'teacher', 'student'
    has_paid = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    taught_courses = db.relationship('Course', backref='teacher', lazy='dynamic')
    enrollments = db.relationship('Enrollment', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    quiz_submissions = db.relationship('QuizSubmission', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    essay_submissions = db.relationship('EssaySubmission', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    discussions = db.relationship('Discussion', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    replies = db.relationship('Reply', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}"

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.user_type == 'admin'

    @property
    def is_teacher(self):
        """Check if user is teacher"""
        return self.user_type == 'teacher'

    @property
    def is_student(self):
        """Check if user is student"""
        return self.user_type == 'student'

    def can_access_course(self, course_id):
        """Check if user can access course (teacher or enrolled student)"""
        if self.is_teacher:
            course = Course.query.get(course_id)
            return course and course.teacher_id == self.id
        elif self.is_student:
            enrollment = Enrollment.query.filter_by(
                student_id=self.id,
                course_id=course_id,
                status='approved'
            ).first()
            return enrollment is not None
        return False


# ================================
# COURSE MODEL
# ================================
class Course(db.Model):
    """Biology course model"""

    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_level = db.Column(db.String(50), nullable=False)  # 'Lower Secondary', 'Advanced Level'
    max_students = db.Column(db.Integer, default=50)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    # FIXED: Matched this to 'users.id' because User table is named 'users'
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # Relationships
    modules = db.relationship('Module', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    enrollments = db.relationship('Enrollment', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    quizzes = db.relationship('Quiz', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    essays = db.relationship('Essay', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    live_classes = db.relationship('LiveClass', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    discussions = db.relationship('Discussion', backref='course', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def enrolled_count(self):
        """Return number of approved enrollments"""
        return self.enrollments.filter_by(status='approved').count()

    @property
    def is_full(self):
        """Check if course is full"""
        return self.enrolled_count >= self.max_students
class Enrollment(db.Model):
    """Student enrollment in courses"""

    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'declined'
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    # Foreign keys
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='unique_enrollment'),)


# ================================
# CURRICULUM MODELS
# ================================

class Module(db.Model):
    """Module within a course"""

    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)

    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    # Relationships
    topics = db.relationship('Topic', backref='module', lazy='dynamic', cascade='all, delete-orphan')


class Topic(db.Model):
    """Topic within a module"""

    __tablename__ = 'topics'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)

    # Foreign keys
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)

    # Relationships
    lessons = db.relationship('Lesson', backref='topic', lazy='dynamic', cascade='all, delete-orphan')


class Lesson(db.Model):
    """Lesson within a topic"""

    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    theory_text = db.Column(db.Text)  # Biology theory content
    video_url = db.Column(db.String(500))  # External video URL (YouTube, etc.)
    video_file = db.Column(db.String(200))  # Uploaded video file
    image_files = db.Column(db.Text)  # Comma-separated list of image/diagram files
    is_lab_lesson = db.Column(db.Boolean, default=False)  # Practical lab lesson flag
    order = db.Column(db.Integer, default=0)

    # Foreign keys
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)


# ================================
# QUIZ MODELS
# ================================

class Quiz(db.Model):
    """Biology quiz assignment"""

    __tablename__ = 'quizzes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    total_points = db.Column(db.Integer, default=0)  # Sum of all question points
    quiz_type = db.Column(db.String(20), default='objective')  # objective, qa, drawing
    time_limit = db.Column(db.Integer, default=0)  # Minutes allowed for timed quizzes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=True)

    # Relationships
    questions = db.relationship('QuizQuestion', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    submissions = db.relationship('QuizSubmission', backref='quiz', lazy='dynamic', cascade='all, delete-orphan')
    topic = db.relationship('Topic', backref='quizzes', foreign_keys=[topic_id])
    module = db.relationship('Module', backref='quizzes', foreign_keys=[module_id])


class QuizQuestion(db.Model):
    """Question within a quiz"""

    __tablename__ = 'quiz_questions'

    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='objective')  # objective, qa, drawing
    option_a = db.Column(db.String(500), nullable=True)
    option_b = db.Column(db.String(500), nullable=True)
    option_c = db.Column(db.String(500), nullable=True)
    option_d = db.Column(db.String(500), nullable=True)
    correct_option = db.Column(db.String(1), nullable=True)  # 'A', 'B', 'C', or 'D'
    points = db.Column(db.Integer, default=1)

    # Foreign keys
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)


class QuizSubmission(db.Model):
    """Student quiz submission"""

    __tablename__ = 'quiz_submissions'

    id = db.Column(db.Integer, primary_key=True)
    total_score = db.Column(db.Integer, default=0)
    graded = db.Column(db.Boolean, default=False)
    graded_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)

    # Relationships
    answers = db.relationship('QuizAnswer', backref='submission', lazy='dynamic', cascade='all, delete-orphan')


class QuizAnswer(db.Model):
    """Student answer to a quiz question"""

    __tablename__ = 'quiz_answers'

    id = db.Column(db.Integer, primary_key=True)
    selected_option = db.Column(db.String(1), nullable=True)  # 'A', 'B', 'C', or 'D'
    text_answer = db.Column(db.Text, nullable=True)
    drawing_path = db.Column(db.String(500), nullable=True)
    teacher_feedback = db.Column(db.Text, nullable=True)
    points_earned = db.Column(db.Integer, default=0)

    # Foreign keys
    submission_id = db.Column(db.Integer, db.ForeignKey('quiz_submissions.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_questions.id'), nullable=False)

    # Relationships
    question = db.relationship('QuizQuestion', backref='answers', foreign_keys=[question_id])


# ================================
# ESSAY MODELS
# ================================

class Essay(db.Model):
    """Biology essay assignment"""

    __tablename__ = 'essays'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    allows_file_upload = db.Column(db.Boolean, default=False)  # Allow file-based submissions
    max_points = db.Column(db.Integer, default=100)
    due_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)

    # Relationships
    submissions = db.relationship('EssaySubmission', backref='essay', lazy='dynamic', cascade='all, delete-orphan')


class EssaySubmission(db.Model):
    """Student essay submission"""

    __tablename__ = 'essay_submissions'

    id = db.Column(db.Integer, primary_key=True)
    text_content = db.Column(db.Text)  # Text-based submission
    uploaded_file = db.Column(db.String(200))  # File-based submission
    score = db.Column(db.Integer)
    feedback = db.Column(db.Text)
    graded = db.Column(db.Boolean, default=False)
    graded_at = db.Column(db.DateTime)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    essay_id = db.Column(db.Integer, db.ForeignKey('essays.id'), nullable=False)


# ================================
# LIVE CLASS MODEL
# ================================

class LiveClass(db.Model):
    """Live biology class session"""

    __tablename__ = 'live_classes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    stream_url = db.Column(db.String(500))  # Streaming URL
    is_active = db.Column(db.Boolean, default=False)  # Only one active class per course
    started_at = db.Column(db.DateTime)
    ended_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)


# ================================
# DISCUSSION MODELS
# ================================

class Discussion(db.Model):
    """Course discussion thread"""

    __tablename__ = 'discussions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    replies = db.relationship('Reply', backref='discussion', lazy='dynamic', cascade='all, delete-orphan')


class Reply(db.Model):
    """Reply to a discussion"""

    __tablename__ = 'replies'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussions.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)


# ================================
# NOTIFICATION MODEL
# ================================

class Notification(db.Model):
    """System notifications for students"""

    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)

    # Foreign keys
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    @property
    def is_read(self):
        """Check if notification has been read"""
        return self.read_at is not None


# ================================
# LIBRARY RESOURCE MODEL
# ================================

class LibraryResource(db.Model):
    """Digital biology library resource"""

    __tablename__ = 'library_resources'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    author = db.Column(db.String(200))
    tags = db.Column(db.String(500))  # Comma-separated tags
    category = db.Column(db.String(100))  # e.g., 'PDF', 'Video', 'Audio', 'Image'
    file_name = db.Column(db.String(200), nullable=False)
    file_size = db.Column(db.Integer)  # Size in bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def tags_list(self):
        """Return tags as a list"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []

    @property
    def file_extension(self):
        """Get file extension"""
        return self.file_name.rsplit('.', 1)[1].lower() if '.' in self.file_name else ''

# ================================
# STUDENT QUESTIONS & TEACHER ANSWERS
# ================================

class StudentQuestion(db.Model):
    """Questions asked by students to all teachers"""

    __tablename__ = 'student_questions'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    content = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='text')  # text, voice, image, mixed
    attachment_path = db.Column(db.String(500))  # Path to image or voice file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_resolved = db.Column(db.Boolean, default=False)

    # Foreign keys
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    student = db.relationship('User', backref='asked_questions', foreign_keys=[student_id])
    answers = db.relationship('TeacherAnswer', backref='question', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def answer_count(self):
        """Get number of answers"""
        return self.answers.count()

    @property
    def answered_by(self):
        """Get list of teachers who answered"""
        return [ans.teacher for ans in self.answers.all()]


class TeacherAnswer(db.Model):
    """Answers provided by teachers to student questions"""

    __tablename__ = 'teacher_answers'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    answer_type = db.Column(db.String(20), default='text')  # text, voice, image, mixed
    attachment_path = db.Column(db.String(500))  # Path to image or voice file
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_flagged = db.Column(db.Boolean, default=False)

    # Foreign keys
    question_id = db.Column(db.Integer, db.ForeignKey('student_questions.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Relationships
    teacher = db.relationship('User', backref='given_answers', foreign_keys=[teacher_id])
