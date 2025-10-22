# app.py
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import csv, datetime, pathlib, os, time

# ---------- CSV helper (Windows/PythonAnywhere lock-safe) ----------
def append_csv_row(csv_path: pathlib.Path, headers, row):
    for _ in range(6):  # ~3 seconds total
        try:
            new = not csv_path.exists()
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with csv_path.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if new:
                    w.writerow(headers)
                w.writerow(row)
            return True
        except PermissionError:
            time.sleep(0.5)
    return False
# -------------------------------------------------------------------

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "dev"
app.config["BRAND"] = "VAGR TECHNOLOGY"

# 🔁 DEV: live-reload templates & avoid stale static files
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.jinja_env.auto_reload = True

@app.after_request
def _no_cache(resp):
    # Dev-only: make sure browser doesn't cache CSS/HTML
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

# Upload settings
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {"pdf"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.errorhandler(RequestEntityTooLarge)
def too_large(e):
    return render_template("careers.html", jobs=JOBS,
                           message="File too large. Max 5 MB."), 413

# ------------ Routes ------------
@app.get("/")
def home():
    return render_template("index.html")

@app.post("/contact")
def contact():
    name = request.form.get("name","").strip()
    email = request.form.get("email","").strip()
    message = request.form.get("message","").strip()
    if not (name and email and message):
        return redirect(url_for("home"))

    csv_path = pathlib.Path(app.instance_path) / "data" / "uploads" / "contacts.csv"
    append_csv_row(
        csv_path,
        headers=["timestamp","name","email","message"],
        row=[datetime.datetime.utcnow().isoformat(), name, email, message]
    )
    return render_template("index.html", message="Thanks! We received your enquiry.")

# Careers data
JOBS = [
    {"title":"Frontend Engineer","location":"Madurai / Remote","type":"Full-time","level":"Mid-Senior"},
    {"title":"Backend Engineer","location":"Madurai / Remote","type":"Full-time","level":"Senior"},
    {"title":"Database","location":"Remote","type":"Full-time","level":"Mid"},
]

@app.get("/careers")
def careers():
    return render_template("careers.html", jobs=JOBS)

@app.post("/apply")
def apply():
    name = request.form.get("name","").strip()
    email = request.form.get("email","").strip()
    role = request.form.get("role","").strip()
    note = request.form.get("note","").strip()
    file = request.files.get("resume")  # PDF file field

    if not (name and email and role and file and file.filename):
        return render_template("careers.html", jobs=JOBS,
                               message="Please fill all fields and attach a PDF.")

    if not allowed_file(file.filename):
        return render_template("careers.html", jobs=JOBS,
                               message="Invalid file type. PDF only.")

    # Save resume -> instance/data/uploads/resumes/<timestamp>_<safe>.pdf
    base_dir = pathlib.Path(app.instance_path) / "data" / "uploads"
    resumes_dir = base_dir / "resumes"
    resumes_dir.mkdir(parents=True, exist_ok=True)

    safe_name = secure_filename(file.filename)
    stamped = f"{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}_{safe_name}"
    save_path = resumes_dir / stamped
    file.save(save_path)

    # light mimetype guard
    if not (file.mimetype or "").lower().endswith("pdf"):
        try: os.remove(save_path)
        except OSError: pass
        return render_template("careers.html", jobs=JOBS,
                               message="Invalid file content. PDF only.")

    # Log to CSV -> instance/data/uploads/application.csv
    csv_path = base_dir / "application.csv"
    append_csv_row(
        csv_path,
        headers=["timestamp","name","email","role","note","resume_file"],
        row=[datetime.datetime.utcnow().isoformat(), name, email, role, note, stamped]
    )

    return render_template("careers.html", jobs=JOBS,
                           message="Application submitted with resume. Thank you!")
# -------------------------------

# Debug helper
@app.get("/__paths")
def paths():
    return {"instance": app.instance_path}

if __name__ == "__main__":
    print("INSTANCE =", app.instance_path)
    # 👇 choose your port here (e.g., 5001)
    app.run(debug=True, port=5001)
