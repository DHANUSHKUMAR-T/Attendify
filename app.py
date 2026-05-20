"""
Student Attendance Management System
=====================================
Flask application with SQLite database
Handles registration, login, and attendance tracking
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import io
import random
import openpyxl
from openpyxl.styles import Font
from datetime import date, datetime
from functools import wraps
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ─────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "sams_secret_key_2024"   # Change this in production!

DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")

# Strict Attendance Settings
ADMIN_PASSWORD = "admin123"
ADMIN_CLEAR_SECRET = "CLEAR2024"

# Global PIN for attendance marking
CURRENT_PIN = None

# Google Sheets Configuration
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Thkg9MvtngFwsOD6PadpgJe7C7RbVYz2dfUW_3CgyCc/edit"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "service_account.json")

def sync_to_google_sheets(data):
    """
    Sync attendance data to Google Sheets.
    data: dict with date, time, reg_no, name, course, status
    """
    if not os.path.exists(CREDENTIALS_FILE):
        print("Google Sheets Sync: service_account.json not found. Skipping sync.")
        return False
    
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(SHEET_URL).sheet1
        
        # Append row: Date, Time, Reg No, Name, Course, Status
        sheet.append_row([
            data.get('date'),
            data.get('time'),
            data.get('reg_no'),
            data.get('name'),
            data.get('course'),
            data.get('status')
        ])
        return True
    except Exception as e:
        print(f"Google Sheets Sync Error: {e}")
        return False


# ─────────────────────────────────────────
# Database Helper
# ─────────────────────────────────────────
def get_db():
    """Return a database connection with row_factory for dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")   # enforce foreign key constraints
    return conn


def init_db():
    """Create tables if they do not already exist."""
    with get_db() as conn:
        conn.executescript("""
            -- Students table: stores registration details
            CREATE TABLE IF NOT EXISTS students (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                register_number TEXT    NOT NULL UNIQUE,
                name            TEXT    NOT NULL,
                course          TEXT    NOT NULL,
                mobile          TEXT    NOT NULL,
                alt_mobile      TEXT,
                password        TEXT    NOT NULL
            );

            -- Attendance table: one record per student per day
            CREATE TABLE IF NOT EXISTS attendance (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                date       TEXT    NOT NULL,
                status     TEXT    NOT NULL CHECK(status IN ('Present', 'Absent')),
                FOREIGN KEY (student_id) REFERENCES students(id),
                UNIQUE (student_id, date)   -- no duplicate entries for same day
            );
        """)


# ─────────────────────────────────────────
# Login Required Decorator
# ─────────────────────────────────────────
def login_required(f):
    """Redirect to login page if the user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "student_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Redirect to admin login if not admin."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            flash("Please log in as Admin to continue.", "warning")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@app.route("/")
def index():
    """Landing page – redirect to login."""
    return redirect(url_for("login"))


# ── Registration ──────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        reg_no   = request.form.get("register_number", "").strip().upper()
        name     = request.form.get("name", "").strip()
        course   = request.form.get("course", "").strip().upper()
        mobile   = request.form.get("mobile", "").strip()
        alt_mob  = request.form.get("alt_mobile", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        # ── Basic validation ─────────────────────
        errors = []
        if not reg_no:
            errors.append("Register number is required.")
        if not name:
            errors.append("Name is required.")
        if not course:
            errors.append("Course is required.")
        if not mobile or not mobile.isdigit() or len(mobile) != 10:
            errors.append("Enter a valid 10-digit mobile number.")
        if alt_mob and (not alt_mob.isdigit() or len(alt_mob) != 10):
            errors.append("Alternative mobile must be a valid 10-digit number.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html",
                                   form=request.form)

        # ── Save to database ─────────────────────
        hashed_pw = generate_password_hash(password)
        try:
            with get_db() as conn:
                conn.execute(
                    """INSERT INTO students
                       (register_number, name, course, mobile, alt_mobile, password)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (reg_no, name, course, mobile, alt_mob or None, hashed_pw)
                )
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Register number already exists. Please use a different one.", "danger")
            return render_template("register.html", form=request.form)

    return render_template("register.html", form={})


# ── Login ─────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if "student_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        reg_no   = request.form.get("register_number", "").strip().upper()
        password = request.form.get("password", "")

        with get_db() as conn:
            student = conn.execute(
                "SELECT * FROM students WHERE register_number = ?", (reg_no,)
            ).fetchone()

        if student and check_password_hash(student["password"], password):
            session["student_id"]       = student["id"]
            session["student_name"]     = student["name"]
            session["register_number"]  = student["register_number"]
            session["course"]           = student["course"]
            flash(f"Welcome back, {student['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid register number or password.", "danger")

    return render_template("login.html")


# ── Logout ────────────────────────────────
@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))


# ── Dashboard ─────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    student_id  = session["student_id"]
    today       = date.today().isoformat()

    with get_db() as conn:
        # Check if attendance already marked for today
        already_marked = conn.execute(
            "SELECT status FROM attendance WHERE student_id = ? AND date = ?",
            (student_id, today)
        ).fetchone()

        # Full attendance history (newest first)
        history = conn.execute(
            """SELECT date, status
               FROM attendance
               WHERE student_id = ?
               ORDER BY date DESC""",
            (student_id,)
        ).fetchall()

        # Statistics
        total     = len(history)
        present   = sum(1 for r in history if r["status"] == "Present")
        absent    = total - present
        pct       = round((present / total * 100), 1) if total > 0 else 0

    return render_template(
        "dashboard.html",
        today          = today,
        already_marked = already_marked,
        history        = history,
        total          = total,
        present        = present,
        absent         = absent,
        percentage     = pct
    )


# ── Mark Attendance ───────────────────────
@app.route("/mark_attendance", methods=["POST"])
@login_required
def mark_attendance():
    global CURRENT_PIN
    student_id = session["student_id"]
    today      = date.today().isoformat()
    status     = request.form.get("status")
    user_pin   = request.form.get("otp_pin")

    # 1. Validate PIN if exists
    if CURRENT_PIN and user_pin != str(CURRENT_PIN):
        flash("Invalid OTP PIN. Please check with your teacher.", "danger")
        return redirect(url_for("dashboard"))

    # 2. Validate Status
    if status not in ("Present", "Absent"):
        flash("Invalid status selection.", "danger")
        return redirect(url_for("dashboard"))

    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO attendance (student_id, date, status)
                   VALUES (?, ?, ?)""",
                (student_id, today, status)
            )
        
        # Sync to Google Sheets
        with get_db() as conn:
            student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
            if student:
                sync_data = {
                    "date": today,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "reg_no": student["register_number"],
                    "name": student["name"],
                    "course": student["course"],
                    "status": status
                }
                sync_to_google_sheets(sync_data)

        flash(f"Attendance marked as {status} for today ({today}).", "success")
    except sqlite3.IntegrityError:
        flash("Attendance for today has already been recorded.", "warning")

    return redirect(url_for("dashboard"))


# ── Admin Routes ──────────────────────────
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if session.get("is_admin"):
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["is_admin"] = True
            flash("Admin login successful.", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin password.", "danger")

    return render_template("admin_login.html")

@app.route("/admin_logout")
def admin_logout():
    session.pop("is_admin", None)
    flash("Admin logged out.", "info")
    return redirect(url_for("admin_login"))

@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():
    # By default show today's attendance for all students
    target_date = request.args.get("date", date.today().isoformat())
    
    with get_db() as conn:
        students = conn.execute("SELECT id, register_number, name, course FROM students").fetchall()
        
        # Get attendance for the target date
        attendance_records = conn.execute(
            "SELECT student_id, status FROM attendance WHERE date = ?", 
            (target_date,)
        ).fetchall()
        
        # Build dictionary mapping student_id -> status
        att_map = {r["student_id"]: r["status"] for r in attendance_records}
        
        # Combine data
        student_data = []
        for s in students:
            student_data.append({
                "id": s["id"],
                "register_number": s["register_number"],
                "name": s["name"],
                "course": s["course"],
                "status": att_map.get(s["id"], "Not Marked")
            })
            
    return render_template("admin_dashboard.html", 
                           students=student_data, 
                           target_date=target_date,
                           current_pin=CURRENT_PIN)

@app.route("/admin/update_attendance", methods=["POST"])
@admin_required
def update_attendance():
    student_id = request.form.get("student_id")
    target_date = request.form.get("date")
    new_status = request.form.get("status")
    
    if new_status not in ("Present", "Absent"):
        flash("Invalid status.", "danger")
        return redirect(url_for("admin_dashboard", date=target_date))
        
    with get_db() as conn:
        # Check if record exists
        existing = conn.execute(
            "SELECT id FROM attendance WHERE student_id = ? AND date = ?", 
            (student_id, target_date)
        ).fetchone()
        
        if existing:
            conn.execute(
                "UPDATE attendance SET status = ? WHERE id = ?", 
                (new_status, existing["id"])
            )
        else:
            conn.execute(
                "INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)",
                (student_id, target_date, new_status)
            )
    
    # Sync to Google Sheets
    with get_db() as conn:
        student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        if student:
            sync_data = {
                "date": target_date,
                "time": datetime.now().strftime("%H:%M:%S"),
                "reg_no": student["register_number"],
                "name": student["name"],
                "course": student["course"],
                "status": new_status
            }
            sync_to_google_sheets(sync_data)
    
    flash(f"Attendance updated to {new_status}.", "success")
    return redirect(url_for("admin_dashboard", date=target_date))


@app.route("/admin/add_student", methods=["POST"])
@admin_required
def admin_add_student():
    reg_no   = request.form.get("register_number", "").strip().upper()
    name     = request.form.get("name", "").strip()
    course   = request.form.get("course", "").strip().upper()
    mobile   = request.form.get("mobile", "").strip()
    password = request.form.get("password", "123456")
    
    if not reg_no or not name:
        flash("Register number and name are required.", "danger")
        return redirect(url_for("admin_dashboard"))
        
    hashed_pw = generate_password_hash(password)
    try:
        with get_db() as conn:
            conn.execute(
                """INSERT INTO students (register_number, name, course, mobile, password)
                   VALUES (?, ?, ?, ?, ?)""",
                (reg_no, name, course, mobile, hashed_pw)
            )
        flash(f"Student {name} added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("Register number already exists.", "danger")
        
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_student/<int:student_id>", methods=["POST"])
@admin_required
def admin_delete_student(student_id):
    with get_db() as conn:
        # Delete attendance first due to foreign key
        conn.execute("DELETE FROM attendance WHERE student_id = ?", (student_id,))
        conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    flash("Student and their attendance records deleted.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/generate_pin", methods=["POST"])
@admin_required
def generate_pin():
    global CURRENT_PIN
    # Generate random 4-digit PIN
    CURRENT_PIN = random.randint(1000, 9999)
    flash(f"New OTP PIN generated: {CURRENT_PIN}", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/export_excel")
@admin_required
def export_excel():
    target_date = request.args.get("date", date.today().isoformat())
    
    with get_db() as conn:
        records = conn.execute("""
            SELECT s.register_number, s.name, s.course, a.status
            FROM students s
            LEFT JOIN attendance a ON s.id = a.student_id AND a.date = ?
            ORDER BY s.register_number ASC
        """, (target_date,)).fetchall()

    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Attendance_{target_date}"

    # Headers
    headers = ["Register Number", "Name", "Course", "Status"]
    ws.append(headers)
    
    # Style headers
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Data
    for row in records:
        ws.append([row["register_number"], row["name"], row["course"], row["status"] or "Not Marked"])

    # Column widths
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15

    # Stream file
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"Attendance_{target_date}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/admin/clear_db", methods=["POST"])
@admin_required
def clear_db():
    pw1 = request.form.get("password1")
    pw2 = request.form.get("password2")
    confirm = request.form.get("confirm")
    
    if pw1 == ADMIN_PASSWORD and pw2 == ADMIN_CLEAR_SECRET and confirm == "yes":
        with get_db() as conn:
            conn.execute("DELETE FROM attendance")
            conn.execute("DELETE FROM students")
        flash("Database cleared successfully (all students and attendance deleted).", "success")
    else:
        flash("Incorrect passwords or confirmation not provided. Action aborted.", "danger")
        
    return redirect(url_for("admin_dashboard"))

# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────
if __name__ == "__main__":
    init_db()          # Create tables on startup
    app.run(debug=True)
