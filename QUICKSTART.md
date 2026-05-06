# Quick Start Guide - The Eagle Biology Class LMS

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies
```bash
cd flask-lms
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### 3. Access the Platform
Open your browser: `http://localhost:5000`

## 👤 Create Your First User

### Register Users
Visit `http://localhost:5000/register` and create:

1. **Admin User**
   - Email: admin@example.com
   - Type: Admin
   - Password: (choose secure password)

2. **Teacher User**
   - Email: teacher@example.com
   - Type: Teacher
   - Password: (choose secure password)

3. **Student User**
   - Email: student@example.com
   - Type: Student
   - Password: (choose secure password)

## 📚 Typical Workflow

### For Admins:
1. Login as admin
2. Go to Admin Dashboard
3. Click "Create New Course"
4. Assign a teacher
5. Manage enrollments from dashboard

### For Teachers:
1. Login as teacher
2. View assigned courses on dashboard
3. Create modules and curriculum
4. Add quizzes and essays
5. Grade student submissions
6. Start live classes

### For Students:
1. Login as student
2. Complete payment (simulated)
3. Browse available courses
4. Request enrollment
5. Access lessons and materials
6. Take quizzes and submit essays
7. View grades

## 🎯 Key Features to Try

### 1. Create a Course (Admin)
- Navigate: Admin Dashboard → Create Course
- Fill in course details
- Assign a teacher

### 2. Build Curriculum (Teacher)
- Navigate: View Course → Create Module
- Add topics to modules
- Add lessons to topics
- Upload videos/images for biology content

### 3. Create Assignments (Teacher)
- **Quiz:** Create Quiz → Add Questions
- **Essay:** Create Essay → Set due date
- Both support biology-focused content

### 4. Student Enrollment (Student)
- Navigate: Make Payment
- Browse Courses → Request Enrollment
- Wait for approval

### 5. Live Class (Teacher)
- Navigate: Course Detail → Start Live Class
- Enter stream URL (YouTube Live, etc.)
- End session when done

### 6. Digital Library (Admin)
- Navigate: Upload Library Resource
- Upload PDFs, videos, diagrams
- Search by title, author, or tags

## 📁 Project Files Overview

```
flask-lms/
├── app.py              # Main application (2018 lines)
├── models.py           # Database models
├── config.py           # Configuration
├── extensions.py       # Flask extensions
├── requirements.txt    # Dependencies
├── uploads/            # File uploads (auto-created)
└── templates/          # HTML templates
    ├── base.html      # Main layout
    ├── index.html     # Landing page
    ├── login.html     # Login form
    ├── register.html  # Registration form
    ├── admin/         # Admin dashboard
    ├── teacher/       # Teacher dashboard
    ├── student/       # Student dashboard
    ├── courses/       # Course pages
    └── errors/        # Error pages (404, 500)
```

## 🔧 Configuration

### Change Port (default: 5000)
Edit `app.py` last line:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Use PostgreSQL
Set environment variable:
```bash
export DATABASE_URL="postgresql://user:password@localhost/dbname"
```

### File Upload Size
Edit `config.py`:
```python
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
```

## 📝 Adding More Templates

The system references these templates (you can add them as needed):

### Course Management
- `courses/create.html` - Create course form
- `courses/edit.html` - Edit course form
- `courses/detail.html` - Course detail page with curriculum

### Curriculum
- `curriculum/create_module.html`
- `curriculum/edit_module.html`
- `curriculum/create_topic.html`
- `curriculum/edit_topic.html`
- `curriculum/create_lesson.html`
- `curriculum/edit_lesson.html`

### Assignments
- `assignments/create_quiz.html`
- `assignments/take_quiz.html`
- `assignments/quiz_submissions.html`
- `assignments/create_essay.html`
- `assignments/submit_essay.html`
- `assignments/essay_submissions.html`
- `assignments/grade_essay.html`

### Live Classes
- `live/start_live_class.html`

### Discussions
- `discussions/create.html`
- `discussions/reply.html`

### Notifications
- `admin/create_notification.html`
- `teacher/create_notification.html`
- `student/notifications.html`

### Library
- `library/index.html`
- `library/upload.html`
- `library/view_pdf.html`

### Student
- `student/grades.html`
- `student/payment.html`

## 🐛 Common Issues

### Port Already in Use
```bash
# Linux/Mac
lsof -i :5000
kill -9 <PID>

# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Database Issues
Delete and recreate:
```bash
rm flask-lms/biology_lms.db
python flask-lms/app.py
```

### Import Errors
Ensure all dependencies installed:
```bash
pip install -r flask-lms/requirements.txt
```

## 🎨 Customization

### Change Colors
Edit `templates/base.html`:
```css
:root {
    --biology-green: #2E7D32;  /* Primary color */
    --biology-dark-green: #1B5E20;
    --biology-light-green: #4CAF50;
}
```

### Add Biology Images
Replace icons with biology imagery:
- DNA helix
- Cells/microscope
- Plants/animals
- Lab equipment

## 📚 Next Steps

1. **Add More Templates:** Create the referenced HTML templates for full UI
2. **Integrate Payment:** Replace simulated payment with Stripe/PayPal
3. **Add Email:** Configure email notifications (Flask-Mail)
4. **Deploy:** Deploy to Heroku, AWS, or your server
5. **Customize:** Tailor the biology curriculum and content

## 💡 Tips

- Start with admin user to set up initial courses
- Create test accounts for each role
- Explore the database using DB Browser for SQLite
- Check `biology_lms.db` for stored data
- All routes are in `app.py` with clear comments

## 🎓 Learning

The code is well-commented:
- Each route explains its purpose
- Decorators show access control
- Models have clear relationships
- Business logic is straightforward

## 🚀 Production Deployment

### Security Checklist
- [ ] Change SECRET_KEY in config.py
- [ ] Use HTTPS (SSL/TLS)
- [ ] Set debug=False in app.py
- [ ] Use production database (PostgreSQL)
- [ ] Configure proper logging
- [ ] Set up backups
- [ ] Integrate real payment gateway
- [ ] Configure CORS if needed

---

**Need Help?** Check the main README.md or review the code comments.
