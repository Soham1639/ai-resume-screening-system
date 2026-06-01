import os
import fitz
import sqlite3
import uuid
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session, send_from_directory

SKILLS_DB = [
    "python", "java", "c++", "sql",
    "machine learning", "deep learning",
    "pandas", "numpy", "scikit-learn",
    "tensorflow", "flask", "django",
    "html", "css", "javascript",
    "react", "node", "spring",
    "data analysis", "statistics",
    "docker", "kubernetes",
    "aws", "git"
]

JOB_KEYWORDS = {
    "data scientist": [
        "python", "machine learning", "pandas", "numpy",
        "statistics", "sql", "data analysis", "scikit-learn"
    ],
    "web developer": [
        "html", "css", "javascript", "flask",
        "react", "api", "backend", "frontend"
    ],
    "java developer": [
        "java", "spring", "oop", "jdbc",
        "hibernate", "sql", "multithreading"
    ],
    "software engineer": [
    "java", "python", "c++", "oop",
    "data structures", "algorithms",
    "sql", "problem solving"
]
}

SUGGESTION_DB = {
    "python": "Build Python automation or data analysis projects.",
    "machine learning": "Create a machine learning project using Scikit-learn.",
    "deep learning": "Build a neural network project using TensorFlow or PyTorch.",
    "pandas": "Practice data cleaning and analysis using Pandas.",
    "numpy": "Learn numerical computing and array operations with NumPy.",
    "statistics": "Study probability, hypothesis testing, and descriptive statistics.",
    "sql": "Practice writing complex SQL queries and joins.",
    "scikit-learn": "Implement classification and regression models using Scikit-learn.",
    "flask": "Build and deploy a Flask web application.",
    "django": "Create a full-stack web application using Django.",
    "html": "Develop responsive web pages using HTML and CSS.",
    "css": "Improve frontend styling and responsive design skills.",
    "javascript": "Build interactive web applications using JavaScript.",
    "react": "Create modern frontend projects using React.",
    "java": "Work on OOP and backend development projects in Java.",
    "spring": "Learn Spring Boot and build REST APIs.",
    "docker": "Containerize applications using Docker.",
    "kubernetes": "Learn container orchestration with Kubernetes.",
    "aws": "Explore cloud deployment and AWS services.",
    "git": "Use Git and GitHub for version control and collaboration."
}

def score_resume(resume_text, job_role):
    keywords = JOB_KEYWORDS.get(job_role.lower(), [])
    score = 0
    matched_keywords = []

    for word in keywords:
        if word in resume_text:
            score += 1
            matched_keywords.append(word)

    return score, matched_keywords

def init_db():
    conn=sqlite3.connect('database.db')
    cursor=conn.cursor()
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS applicants(
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   name TEXT,
                   email TEXT,
                   job_role TEXT,
                   percentage INTEGER,
                   decision TEXT,
                   resume_file TEXT,
                   timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)
                   """)
    conn.commit()
    conn.close()

def extract_text_from_pdf(pdf_path):
    text=""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text+=page.get_text()
    return text

def clean_text(text):
    text=text.lower()
    text=" ".join(text.split())
    return text

def extract_skills(resume_text):

    detected_skills = []

    for skill in SKILLS_DB:
        if skill in resume_text:
            detected_skills.append(skill)

    return detected_skills

def recommend_jobs(skills_found):
    recommendations = []

    for role, keywords in JOB_KEYWORDS.items():
        match_count = 0

        for skill in skills_found:
            if skill in keywords:
                match_count += 1

        if len(keywords) == 0:
            continue

        score = (match_count / len(keywords)) * 100

        if match_count > 0:
            recommendations.append((role.title(), round(score, 2)))

    recommendations.sort(key=lambda x: x[1], reverse=True)

    return recommendations

def get_skill_gap(job_role, skills_found):

    required_skills = JOB_KEYWORDS.get(job_role.lower(), [])

    missing_skills = []

    for skill in required_skills:
        if skill not in skills_found:
            missing_skills.append(skill)

    return missing_skills

def generate_feedback(resume_text, job_role):
    keywords = JOB_KEYWORDS.get(job_role.lower(), [])

    matched = [k for k in keywords if k in resume_text]
    missing = [k for k in keywords if k not in resume_text]

    score = len(matched)

    if score >= 4:
        decision = "Shortlisted"
        message = f"Great! Your resume matches the {job_role} role well."
    else:
        decision = "Rejected"
        message = f"Your resume needs more relevant skills for the {job_role} role."

    return score, matched, missing, decision, message

def generate_suggestions(missing_skills):

    suggestions = []

    for skill in missing_skills:
        if skill in SUGGESTION_DB:
            suggestions.append(SUGGESTION_DB[skill])
        else:
            suggestions.append(
                f"Consider learning {skill}."
            )
    return suggestions

app = Flask(__name__)
app.secret_key = "supersecretkey"
UPLOAD_FOLDER = 'uploads'
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

@app.route('/',methods=["GET","POST"])
def home():

    skills_found=None
    percentage=None
    decision=None
    recommended_jobs=None

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        job = request.form.get("job_role")
        resume = request.files.get("resume")
        
        if resume:
            unique_id = str(uuid.uuid4())
            filename = unique_id + "_" + secure_filename(resume.filename)
            file_path=os.path.join(app.config["UPLOAD_FOLDER"],filename)
            resume.save(file_path)

            resume_text = extract_text_from_pdf(file_path)
            resume_text = clean_text(resume_text)
            skills_found = extract_skills(resume_text)
            recommended_jobs = recommend_jobs(skills_found)
            missing_skills = get_skill_gap(job, skills_found)
            print("Detected Skills:", skills_found)
            
            score, matched, missing, decision, message = generate_feedback(resume_text, job)
            suggestions = generate_suggestions(missing)
            keywords = JOB_KEYWORDS.get(job.lower(), [])
            if len(keywords) > 0:
                percentage = int((score / len(keywords)) * 100)
            else:
                percentage = 0

            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO applicants (name, email, job_role, percentage, decision,resume_file)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, email, job, percentage, decision, filename))

            conn.commit()
            cursor.execute("SELECT * FROM applicants")
            print(cursor.fetchall())

            conn.close()

            return render_template(
            "results.html",
            skills=skills_found,
            matched=matched,
            missing=missing,
            suggestions=suggestions,
            score=score,
            percentage=percentage,
            decision=decision,
            recommendations=recommended_jobs
            )

    return render_template("index.html")


@app.route('/admin')
def admin():

    if not session.get("admin"):
        return redirect("/admin_login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM applicants")
    applicants = cursor.fetchall()

    conn.close()

    return render_template('admin.html', applicants=applicants)

@app.route('/admin_login', methods=["GET","POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "admin" and password == "admin123":
            session["admin"] = True
            return redirect("/admin")

        else:
            return "Invalid credentials"

    return render_template("admin_login.html")

@app.route("/download/<filename>")
def download_resume(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/delete/<int:id>")
def delete_applicant(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM applicants WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/admin")

if __name__ == '__main__':
    app.run()