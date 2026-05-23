"""
Student Attendance Management System
=====================================
Flask application with MongoDB backend
Handles registration, login, and attendance tracking
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
import random
import openpyxl
from openpyxl.styles import Font
from datetime import date, datetime
from functools import wraps
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pymongo import MongoClient
from bson import ObjectId

# ─────────────────────────────────────────
# App Configuration
# ─────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "sams_secret_key_2024"   # Change this in production!

# MongoDB connection – use environment variable MONGO_URI
# MongoDB Connection String
MONGO_URI = "mongodb+srv://tdhanu:Dhanu123@clustersumma.ggzzczb.mongodb.net/attendance_db?retryWrites=true&w=majority&appName=ClusterSumma"

# Connect MongoDB
client = MongoClient(MONGO_URI)

# Database
db = client["attendance_db"]

# Collections
students_collection = db["students"]
attendance_collection = db["attendance"]

# Ensure unique index on register_number
students_collection.create_index("register_number", unique=True)

# Strict Attendance Settings
ADMIN_PASSWORD = "admin123"
ADMIN_CLEAR_SECRET = "CLEAR2024"

# Global PIN for attendance marking
CURRENT_PIN = None

# Google Sheets Configuration
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Thkg9MvtngFwsOD6PadpgJe7C7RbVYz2dfUW_3CgyCc/edit"
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "service_account.json")

def sync_to_google_sheets(data):
    """Sync attendance data to Google Sheets.
    data: dict with date, time, reg_no, name, course, status
    """
    if not os.path.exists(CREDENTIALS_FILE):
        print("Google Sheets Sync: service_account.json not found. Skipping sync.")
        return False
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client_gs = gspread.authorize(creds)
        sheet = client_gs.open_by_url(SHEET_URL).sheet1
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
# Login Required Decorator
# ─────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "student_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
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
    return redirect(url_for("login"))

# ── Registration ──────────────────────────
@app.route("/register", methods=["GET", "POST"]) 
def register():
    if request.method == "POST":
        reg_no = request.form.get("register_number", "").strip().upper()
        name = request.form.get("name", "").strip()
        course = request.form.get("course", "").strip().upper()
        mobile = request.form.get("mobile", "").strip()
        alt_mob = request.form.get("alt_mobile", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not reg_no:
            errors.append("Register number is required.")
        if not name:
            errors.append("Name is required.")
        if not course:
            errors.append("Course is required.")
        if not mobile.isdigit() or len(mobile) != 10:
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
            return render_template("register.html", form=request.form)

        hashed_pw = generate_password_hash(password)
        try:
            students_collection.insert_one({
                "register_number": reg_no,
                "name": name,
                "course": course,
                "mobile": mobile,
                "alt_mobile": alt_mob or None,
                "password": hashed_pw
            })
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash("Register number already exists or database error.", "danger")
            return render_template("register.html", form=request.form)
    return render_template("register.html", form={})

# ── Login ─────────────────────────────────
@app.route("/login", methods=["GET", "POST"]) 
def login():
    if "student_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        reg_no = request.form.get("register_number", "").strip().upper()
        password = request.form.get("password", "")
        student = students_collection.find_one({"register_number": reg_no})
        if student and check_password_hash(student["password"], password):
            session["student_id"] = str(student["_id"])
            session["student_name"] = student["name"]
            session["register_number"] = student["register_number"]
            session["course"] = student["course"]
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
    student_id = session["student_id"]
    today = date.today().isoformat()

    # Attendance for today
    already_marked_doc = attendance_collection.find_one({"student_id": ObjectId(student_id), "date": today})
    already_marked = already_marked_doc["status"] if already_marked_doc else None

    # Full history (newest first)
    history_cursor = attendance_collection.find({"student_id": ObjectId(student_id)}).sort("date", -1)
    history = list(history_cursor)

    total = len(history)
    present = sum(1 for r in history if r.get("status") == "Present")
    absent = total - present
    pct = round((present / total * 100), 1) if total > 0 else 0

    return render_template(
        "dashboard.html",
        today=today,
        already_marked=already_marked,
        history=history,
        total=total,
        present=present,
        absent=absent,
        percentage=pct
    )

# ── Mark Attendance ───────────────────────
@app.route("/mark_attendance", methods=["POST"])
@login_required
def mark_attendance():
    global CURRENT_PIN
    student_id = session["student_id"]
    today = date.today().isoformat()
    status = request.form.get("status")
    user_pin = request.form.get("otp_pin")

    if CURRENT_PIN and user_pin != str(CURRENT_PIN):
        flash("Invalid OTP PIN. Please check with your teacher.", "danger")
        return redirect(url_for("dashboard"))
    if status not in ("Present", "Absent"):
        flash("Invalid status selection.", "danger")
        return redirect(url_for("dashboard"))

    try:
        attendance_collection.insert_one({
            "student_id": ObjectId(student_id),
            "date": today,
            "status": status
        })
        # Sync to Google Sheets
        student = students_collection.find_one({"_id": ObjectId(student_id)})
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
    except Exception as e:
        flash("Attendance for today has already been recorded or an error occurred.", "warning")
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
    target_date = request.args.get("date", date.today().isoformat())
    students = list(students_collection.find({}, {"register_number": 1, "name": 1, "course": 1}))
    attendance_records = list(attendance_collection.find({"date": target_date}, {"student_id": 1, "status": 1}))
    att_map = {str(rec["student_id"]): rec["status"] for rec in attendance_records}
    student_data = []
    for s in students:
        sid = str(s["_id"])
        student_data.append({
            "id": sid,
            "register_number": s["register_number"],
            "name": s["name"],
            "course": s["course"],
            "status": att_map.get(sid, "Not Marked")
        })
    return render_template("admin_dashboard.html", students=student_data, target_date=target_date, current_pin=CURRENT_PIN)

@app.route("/admin/update_attendance", methods=["POST"])
@admin_required
def update_attendance():
    student_id = request.form.get("student_id")
    target_date = request.form.get("date")
    new_status = request.form.get("status")
    if new_status not in ("Present", "Absent"):
        flash("Invalid status.", "danger")
        return redirect(url_for("admin_dashboard", date=target_date))
    existing = attendance_collection.find_one({"student_id": ObjectId(student_id), "date": target_date})
    if existing:
        attendance_collection.update_one({"_id": existing["_id"]}, {"$set": {"status": new_status}})
    else:
        attendance_collection.insert_one({"student_id": ObjectId(student_id), "date": target_date, "status": new_status})
    # Sync to Google Sheets
    student = students_collection.find_one({"_id": ObjectId(student_id)})
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
    reg_no = request.form.get("register_number", "").strip().upper()
    name = request.form.get("name", "").strip()
    course = request.form.get("course", "").strip().upper()
    mobile = request.form.get("mobile", "").strip()
    password = request.form.get("password", "123456")
    if not reg_no or not name:
        flash("Register number and name are required.", "danger")
        return redirect(url_for("admin_dashboard"))
    hashed_pw = generate_password_hash(password)
    try:
        students_collection.insert_one({
            "register_number": reg_no,
            "name": name,
            "course": course,
            "mobile": mobile,
            "password": hashed_pw
        })
        flash(f"Student {name} added successfully.", "success")
    except Exception as e:
        flash("Register number already exists.", "danger")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete_student/<string:student_id>", methods=["POST"])
@admin_required
def admin_delete_student(student_id):
    attendance_collection.delete_many({"student_id": ObjectId(student_id)})
    students_collection.delete_one({"_id": ObjectId(student_id)})
    flash("Student and their attendance records deleted.", "info")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/generate_pin", methods=["POST"])
@admin_required
def generate_pin():
    global CURRENT_PIN
    CURRENT_PIN = random.randint(1000, 9999)
    flash(f"New OTP PIN generated: {CURRENT_PIN}", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/export_excel")
@admin_required
def export_excel():
    target_date = request.args.get("date", date.today().isoformat())
    records = list(attendance_collection.aggregate([
        {"$match": {"date": target_date}},
        {"$lookup": {
            "from": "students",
            "localField": "student_id",
            "foreignField": "_id",
            "as": "student"
        }},
        {"$unwind": "$student"},
        {"$project": {
            "register_number": "$student.register_number",
            "name": "$student.name",
            "course": "$student.course",
            "status": "$status"
        }},
        {"$sort": {"register_number": 1}}
    ]))
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Attendance_{target_date}"
    headers = ["Register Number", "Name", "Course", "Status"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for r in records:
        ws.append([r.get("register_number"), r.get("name"), r.get("course"), r.get("status")])
    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 15
    ws.column_dimensions['D'].width = 15
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"Attendance_{target_date}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

@app.route("/admin/clear_db", methods=["POST"])
@admin_required
def clear_db():
    pw1 = request.form.get("password1")
    pw2 = request.form.get("password2")
    confirm = request.form.get("confirm")
    if pw1 == ADMIN_PASSWORD and pw2 == ADMIN_CLEAR_SECRET and confirm == "yes":
        attendance_collection.delete_many({})
        students_collection.delete_many({})
        flash("Database cleared successfully (all students and attendance deleted).", "success")
    else:
        flash("Incorrect passwords or confirmation not provided. Action aborted.", "danger")
    return redirect(url_for("admin_dashboard"))

# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
