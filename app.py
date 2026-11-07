"""CareerLens: local-first resume and job-description matching dashboard."""
import io
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE = Path(__file__).resolve().parent
SKILLS = ["python", "sql", "machine learning", "deep learning", "natural language processing", "nlp", "data analysis", "data visualization", "flask", "django", "fastapi", "react", "javascript", "html", "css", "git", "github", "docker", "aws", "azure", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "excel", "power bi", "tableau", "communication", "leadership", "project management", "api", "rest api", "linux", "postgresql", "sqlite", "testing", "statistics", "computer vision", "cloud computing"]


def extract_skills(text):
    low = text.lower()
    return sorted({skill for skill in SKILLS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", low)})


def analyze(resume, job):
    if not resume.strip() or not job.strip():
        raise ValueError("Both resume and job description are required.")
    vectors = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform([resume, job])
    similarity = round(float(cosine_similarity(vectors[0], vectors[1])[0][0]) * 100, 1)
    found = extract_skills(resume)
    expected = extract_skills(job)
    matched = sorted(set(found) & set(expected))
    missing = sorted(set(expected) - set(found))
    coverage = round(100 * len(matched) / len(expected), 1) if expected else None
    return {"similarity": similarity, "coverage": coverage, "matched": matched, "missing": missing, "resume_skills": found, "job_skills": expected, "tips": (["Mention relevant skills you genuinely possess, with project evidence." ] if missing else ["Strong skill coverage. Highlight measurable achievements and relevant projects."]) + ["Use specific accomplishments and tailor the summary to the role."]}


def extract_file(upload):
    name = (upload.filename or "").lower()
    data = upload.read(3 * 1024 * 1024 + 1)
    if len(data) > 3 * 1024 * 1024:
        raise ValueError("File exceeds the 3 MB limit.")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
    if name.endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
    if name.endswith(".txt"):
        return data.decode("utf-8-sig")
    raise ValueError("Upload a PDF, DOCX, or TXT file.")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get("CAREERLENS_SECRET", "local-development-only"), DATABASE=str(BASE / "careerlens.sqlite3"), MAX_CONTENT_LENGTH=4 * 1024 * 1024)
    if test_config:
        app.config.update(test_config)

    def connection():
        db = sqlite3.connect(app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE IF NOT EXISTS analyses (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, role TEXT NOT NULL, similarity REAL NOT NULL, coverage REAL, matched TEXT NOT NULL, missing TEXT NOT NULL)")
        db.commit()
        return db

    @app.get("/")
    def index():
        with connection() as db:
            history = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 12").fetchall()
        return render_template("index.html", history=history, result=None)

    @app.post("/analyze")
    def analyze_route():
        role = request.form.get("role", "").strip()[:120] or "Untitled role"
        job = request.form.get("job", "").strip()
        resume = request.form.get("resume", "").strip()
        upload = request.files.get("file")
        try:
            if upload and upload.filename:
                resume = extract_file(upload)
            if len(resume) > 100000 or len(job) > 100000:
                raise ValueError("Text is too long (maximum 100,000 characters per field).")
            result = analyze(resume, job)
        except Exception as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))
        with connection() as db:
            db.execute("INSERT INTO analyses (created_at, role, similarity, coverage, matched, missing) VALUES (?, ?, ?, ?, ?, ?)", (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), role, result["similarity"], result["coverage"], json.dumps(result["matched"]), json.dumps(result["missing"])))
            db.commit()
            history = db.execute("SELECT * FROM analyses ORDER BY id DESC LIMIT 12").fetchall()
        return render_template("index.html", history=history, result=result, role=role, job=job, resume=resume)

    @app.post("/clear")
    def clear():
        with connection() as db:
            db.execute("DELETE FROM analyses")
            db.commit()
        flash("Local analysis history cleared.", "success")
        return redirect(url_for("index"))

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
