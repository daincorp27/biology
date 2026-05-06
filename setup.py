import os

# Define folder structure
folders = [
    'admin',
    'assignments',
    'courses',
    'curriculum',
    'discussions',
    'errors',
    'library',
    'live',
    'student',
    'teacher',
    'lessons' # Added this for the viewer feature
]

# Base path
base_path = os.path.join(os.getcwd(), 'templates')

# 1. Create Folders
print(f"Creating folders in {base_path}...")
for folder in folders:
    path = os.path.join(base_path, folder)
    if not os.path.exists(path):
        os.makedirs(path)
        print(f" [+] Created: {folder}/")
    else:
        print(f" [x] Exists:  {folder}/")

# 2. Define required files (Based on your app.py routes)
files_to_create = {
    'dashboard.html': 'admin',
    'create_teacher.html': 'admin',
    'create_notification.html': 'admin',
    
    'create_quiz.html': 'assignments',
    'take_quiz.html': 'assignments',
    'quiz_submissions.html': 'assignments',
    'create_essay.html': 'assignments',
    'submit_essay.html': 'assignments',
    'essay_submissions.html': 'assignments',
    'grade_essay.html': 'assignments',

    'list.html': 'courses',
    'detail.html': 'courses',
    'create.html': 'courses',
    'edit.html': 'courses',
    
    'create_module.html': 'curriculum',
    'edit_module.html': 'curriculum',
    'create_topic.html': 'curriculum',
    'edit_topic.html': 'curriculum',
    'create_lesson.html': 'curriculum',
    'edit_lesson.html': 'curriculum',
    
    'create.html': 'discussions',
    'reply.html': 'discussions',

    '404.html': 'errors',
    '500.html': 'errors',

    'index.html': 'library',
    'upload.html': 'library',
    'viewer.html': 'library',
    'view_pdf.html': 'library',

    'start_live_class.html': 'live',

    'dashboard.html': 'student',
    'grades.html': 'student',
    'payment.html': 'student',
    'notifications.html': 'student',

    'dashboard.html': 'teacher',
    'create_notification.html': 'teacher',
    
    'view_lesson.html': 'lessons'
}

# 3. Create Empty Files
print("\nCreating empty HTML files...")
for filename, folder in files_to_create.items():
    filepath = os.path.join(base_path, folder, filename)
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            # FIX: Using .format() here instead of f-string to allow Jinja2 syntax
            content = "<!-- {} -->\n{{% extends 'base.html' %}}\n\n{{% block content %}}\n<p>Content for {}</p>\n{{% endblock %}}".format(filename, filename)
            f.write(content)
        print(f" [+] Created: {folder}/{filename}")
    else:
        print(f" [x] Exists:  {folder}/{filename}")

print("\n✅ Template structure setup complete!")