import os
import fitz
import sqlite3
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request

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

app=Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()

@app.route('/',methods=["GET","POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        job = request.form.get("job_role")
        resume = request.files.get("resume")
        
        if resume:
            filename=secure_filename(resume.filename)
            file_path=os.path.join(app.config["UPLOAD_FOLDER"],filename)
            resume.save(file_path)

            resume_text = extract_text_from_pdf(file_path)
            resume_text = clean_text(resume_text)
            
            score, matched, missing, decision, message = generate_feedback(resume_text, job)
            keywords = JOB_KEYWORDS.get(job.lower(), [])
            if len(keywords) > 0:
                percentage = int((score / len(keywords)) * 100)
            else:
                percentage = 0

            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO applicants (name, email, job_role, percentage, decision)
                VALUES (?, ?, ?, ?, ?)
            """, (name, email, job, percentage, decision))

            conn.commit()
            cursor.execute("SELECT * FROM applicants")
            print(cursor.fetchall())

            conn.close()

    return render_template('index.html')

@app.route('/admin')
def admin():
    conn=sqlite3.connect("database.db")
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM applicants")
    applicants=cursor.fetchall()
    conn.close()
    return render_template('admin.html',applicants=applicants)

if __name__ == '__main__':
    app.run()