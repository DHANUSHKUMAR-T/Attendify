# Attendify 🎓✨

**Attendify** is a premium, modern Student Attendance Management System. Featuring a sleek Glassmorphism design and deep styling, it provides an intuitive interface for both students and administrators to manage and track attendance with advanced verification mechanisms.

---

## 🚀 Key Features

### 👨‍🎓 For Students
* **Secure Registration & Login**: Registration using a dedicated register number, full name, course select dropdown, and secure password hashing.
* **OTP PIN Verification**: Students can only mark their attendance by entering a 4-digit OTP PIN generated in real-time by the class teacher/administrator, preventing unauthorized or remote marking.
* **Personal Attendance Dashboard**: Real-time stats showing total classes, present days, absent days, and a visually appealing attendance percentage progress bar.
* **Detailed History**: A complete list of past attendance records.

### 👩‍💼 For Administrators (Teachers)
* **Live OTP PIN Generator**: Instantly generate random, secure 4-digit attendance PINs.
* **Student Account Management**: Effortlessly register new student accounts or permanently delete accounts and their history.
* **Interactive Attendance Grid**: View and search the attendance status of all students for any selected calendar date.
* **Manual Override**: Change any student's attendance status (Present/Absent) on the fly with automatic database updates.
* **Excel Export**: Download complete attendance sheets for any date in `.xlsx` format with a single click.
* **Google Sheets Live Sync**: Automatically appends attendance check-ins to a shared public Google Sheet with real-time timestamps.
* **Safe Wiping (Danger Zone)**: Secure, two-step password-verified mechanism to wipe all students and logs from the database.

---

## 🛠️ Technology Stack

* **Frontend**: HTML5, Vanilla CSS3 (Glassmorphism theme), JavaScript, Google Fonts (Inter), FontAwesome 6 icons.
* **Backend**: Flask (Python).
* **Database**: SQLite3 with foreign keys constraint enforcement.
* **APIs & Libraries**:
  * `gspread` & `oauth2client` for direct Google Sheets synchronization.
  * `openpyxl` for exporting reports dynamically to Microsoft Excel.
  * `werkzeug` for secure password encryption and hashing.

---

## 📋 Course Offerings (Codes Reference)

Attendify comes preconfigured with a streamlined **Course Reference Guide** dropdown. When adding/registering students, the system uses the standard short-form course codes:

* **ADAD** – AI & Data Science
* **ADCHN** – Hardware & Networking
* **ADDA** – Data Analytics
* **ADJP** – Java Programming
* **ADMS** – MERN / MEAN Stack
* **ADPP** – Python Programming
* **ADCA** – Computer Application
* **DCA** – Computer Application
* **DFJD** – Full Stack Java Developer
* **DFPD** – Full Stack Python Developer
* **DMO** – MS Office
* **DPFD** – PHP Full Stack Developer
* **HDCA** – Honours Computer Application
* **HDFD** – Honours Full Stack Developer
* **MDSA** – System Administration
* **CCAE** – Advanced Excel
* **CCA** – Certified Computer Accountant
* **JDCS** – Junior Digital Computer Skills

---

## 💻 Getting Started

### 1. Prerequisites
Make sure you have Python 3 installed on your system.

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/DHANUSHKUMAR-T/Attendify.git
cd Attendify
pip install flask openpyxl gspread oauth2client
```

### 3. Run the App
Start the development server:
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser!

---

## 🧪 Testing

To run the automated test suite, run:
```bash
python -m unittest test_sams.py
```
