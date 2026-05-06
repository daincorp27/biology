# The Eagle Biology Class - Learning Management System

A production-ready Flask-based LMS specifically designed for Biology education.

## 🎯 Features

### User Management
- Three user roles: Admin, Teacher, Student
- Secure authentication with password hashing (Werkzeug)
- Role-based access control (RBAC)

### Course Management
- Create, edit, and delete Biology courses (Admin only)
- Assign teachers to courses
- Two target levels: Lower Secondary / Advanced Level
- Course enrollment limits

### Payment System
- Simulated payment processing for students
- Payment verification before enrollment
- Easy integration with actual payment gateways

### Enrollment System
- Students request enrollment
- Teachers/admin approve or decline requests
- Prevents duplicate enrollments
- Course capacity management

### Curriculum Structure
- **Four-level hierarchy:** Course → Module → Topic → Lesson
- Biology theory content
- Video lessons (URL or uploaded files)
- Diagram/images upload
- Lab lesson flag for practical work
- Sort/order support at all levels

### Assignments

#### Biology Quizzes
- Multiple-choice questions (A/B/C/D)
- Per-question point allocation
- Auto-grading with immediate feedback
- Student submissions tracking

#### Biology Essays
- Text-based submissions
- File-based submissions (PDFs, docs, etc.)
- Teacher grading with feedback
- Due date support

### Grading System
- Quiz auto-grading with percentage calculation
- Essay manual grading
- Student grade dashboard
- Overall performance statistics

### Live Biology Classes
- Teachers start live sessions
- Stream URL support (YouTube Live, Vimeo, etc.)
- Only one active class per course
- Session tracking (start/end times)

### Discussion Forums
- Course-based discussions
- Q&A for biology topics
- Threaded replies with user attribution
- Pinned discussions (teacher only)

### Notifications
- Admin broadcast to all students
- Teacher announcements to course students
- Targeted notifications
- Read/unread tracking

### Digital Biology Library
- Upload resources (PDFs, videos, audio, images)
- Biology metadata (author, tags, category)
- Search and filter functionality
- Online PDF viewing
- Download resources

## 📁 Project Structure

```
flask-lms/
├── app.py                    # Main Flask application (all routes & logic)
├── models.py                 # Database models
├── config.py                 # Configuration
├── extensions.py             # Flask extensions (db, login_manager)
├── requirements.txt          # Python dependencies
├── uploads/                 # File uploads
│   └── library/            # Digital library resources
└── templates/               # Jinja2 templates
    ├── base.html            # Base template
    ├── index.html          # Landing page
    ├── login.html          # Login page
    ├── register.html       # Registration page
    ├── admin/             # Admin templates
    │   └── dashboard.html
    ├── teacher/           # Teacher templates
    │   └── dashboard.html
    ├── student/           # Student templates
    │   ├── dashboard.html
    │   ├── grades.html
    │   ├── payment.html
    │   └── notifications.html
    ├── courses/           # Course management templates
    ├── curriculum/        # Curriculum templates
    ├── assignments/       # Assignment templates
    ├── discussions/      # Discussion templates
    ├── live/             # Live class templates
    ├── library/          # Library templates
    └── errors/           # Error pages
```

## 🚀 Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Setup Steps

1. **Navigate to project directory**
   ```bash
   cd flask-lms
   ```

2. **Create virtual environment (recommended)**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**

   On Windows:
   ```bash
   venv\Scripts\activate
   ```

   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the application**
   Open your browser and visit: `http://localhost:5000`

## 👥 User Roles

### Admin
- Create and manage courses
- Assign teachers to courses
- View system statistics
- Manage enrollments
- Create global notifications
- Manage digital library

### Teacher
- View and manage assigned courses
- Create curriculum (modules, topics, lessons)
- Create and grade quizzes
- Create and grade essays
- Start live classes
- Approve/decline enrollments
- Create course-specific notifications
- Participate in discussions

### Student
- Browse available courses
- Complete payment
- Request enrollment
- View curriculum and lessons
- Take quizzes
- Submit essays
- View grades
- Attend live classes
- Participate in discussions
- Receive notifications
- Access digital library

## 🗄️ Database

The system uses SQLite by default for simplicity, but is PostgreSQL-ready.

### Default SQLite Database
- File: `biology_lms.db` (created automatically)
- No additional configuration needed

### PostgreSQL Setup (Optional)

1. Install PostgreSQL adapter:
   ```bash
   pip install psycopg2-binary
   ```

2. Set environment variable:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost/dbname"
   ```

3. The app will automatically use PostgreSQL if `DATABASE_URL` is set.

### Database Schema

The system includes 15+ database tables:
- Users
- Courses
- Modules
- Topics
- Lessons
- Enrollments
- Quizzes
- Quiz Questions
- Quiz Submissions
- Quiz Answers
- Essays
- Essay Submissions
- Live Classes
- Discussions
- Replies
- Notifications
- Library Resources

## 🎨 Customization

### Biology Theming
The platform is biology-focused. Customize templates in `templates/` directory:
- Add biology imagery (cells, DNA, etc.)
- Use biology terminology throughout
- Color schemes: Green (nature), Blue (science)

### File Uploads
Configure in `config.py`:
```python
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx', 'mp4', 'mp3', 'wav', 'jpg', 'jpeg', 'png', 'gif'}
```

### Payment Integration
Replace the simulated payment in `app.py` with real gateway:
- Stripe
- PayPal
- Braintree
- Square

## 🔒 Security

- Passwords hashed with Werkzeug security
- Role-based access control decorators
- Protected routes with Flask-Login
- File upload validation
- SQL injection prevention (SQLAlchemy ORM)
- XSS protection (Jinja2 auto-escaping)

## 📚 API Routes

### Authentication
- `GET /` - Landing page
- `GET/POST /register` - User registration
- `GET/POST /login` - User login
- `GET /logout` - User logout

### Dashboards
- `GET /dashboard` - Role-based redirect
- `GET /admin/dashboard` - Admin dashboard
- `GET /teacher/dashboard` - Teacher dashboard
- `GET /student/dashboard` - Student dashboard

### Courses
- `GET /courses` - List courses
- `GET /courses/<id>` - Course details
- `POST /admin/courses/create` - Create course
- `POST /admin/courses/<id>/edit` - Edit course
- `POST /admin/courses/<id>/delete` - Delete course

### Curriculum
- `POST /teacher/courses/<id>/modules/create` - Create module
- `POST /teacher/modules/<id>/edit` - Edit module
- `POST /teacher/modules/<id>/delete` - Delete module
- `POST /teacher/modules/<id>/topics/create` - Create topic
- `POST /teacher/topics/<id>/edit` - Edit topic
- `POST /teacher/topics/<id>/delete` - Delete topic
- `POST /teacher/topics/<id>/lessons/create` - Create lesson
- `POST /teacher/lessons/<id>/edit` - Edit lesson
- `POST /teacher/lessons/<id>/delete` - Delete lesson

### Assignments
- `POST /teacher/courses/<id>/quizzes/create` - Create quiz
- `GET/POST /student/quizzes/<id>/take` - Take quiz
- `GET /teacher/quizzes/<id>/submissions` - View submissions
- `POST /teacher/courses/<id>/essays/create` - Create essay
- `GET/POST /student/essays/<id>/submit` - Submit essay
- `GET /teacher/essays/<id>/submissions` - View submissions
- `GET/POST /teacher/essay-submissions/<id>/grade` - Grade essay

### Live Classes
- `GET/POST /teacher/courses/<id>/live-class/start` - Start live class
- `POST /teacher/live-classes/<id>/end` - End live class

### Discussions
- `GET/POST /courses/<id>/discussions/create` - Create discussion
- `GET/POST /discussions/<id>/reply` - Reply to discussion

### Notifications
- `GET/POST /admin/notifications/create` - Create notification
- `GET/POST /teacher/courses/<id>/notifications/create` - Create notification
- `GET /student/notifications` - View notifications
- `POST /student/notifications/<id>/read` - Mark as read

### Library
- `GET /library` - View library (with search/filter)
- `GET/POST /admin/library/upload` - Upload resource
- `GET /library/<id>/view` - View resource
- `GET /library/<id>/download` - Download resource
- `POST /admin/library/<id>/delete` - Delete resource

## 🐛 Troubleshooting

### Database not creating
```bash
# Delete existing database
rm biology_lms.db

# Restart app
python app.py
```

### File upload issues
Check `uploads/` directory permissions:
```bash
chmod 755 uploads/
chmod 755 uploads/library/
```

### Port already in use
Change port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use 5001 instead
```

## 📄 License

This project is provided as-is for educational purposes.

## 👨‍💻 Development

The system follows these principles:
- **Simplicity**: Minimal files, clear structure
- **Clarity**: Well-commented code
- **Maintainability**: Easy to extend
- **Production-ready**: Robust error handling

## 🎓 Biology Education Focus

Designed specifically for biology education:
- Lab lesson support for practical work
- Digital library for biology resources
- Diagram/image upload for visual learning
- Structured curriculum (modules/topics/lessons)
- Discussion forums for biology Q&A

## 📞 Support

For issues or questions, please refer to the code comments or modify as needed.

---

**Built with ❤️ for Biology Education**
