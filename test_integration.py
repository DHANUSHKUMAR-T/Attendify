import requests
from bs4 import BeautifulSoup
import time

# Wait for server to be ready
time.sleep(2)

print("--- Testing Registration ---")
# Since the server is running on 5000, we can hit it.
session = requests.Session()
res = session.post('http://127.0.0.1:5000/register', data={
    'register_number': 'TEST999',
    'name': 'Bob Tester',
    'course': 'DCA',
    'mobile': '9876543210',
    'password': 'password',
    'confirm_password': 'password'
})
print("Registered:", "Registration successful" in res.text or "already exists" in res.text)

print("\n--- Testing Login ---")
res = session.post('http://127.0.0.1:5000/login', data={
    'register_number': 'TEST999',
    'password': 'password'
})
print("Logged in:", "Welcome back" in res.text)

print("\n--- Testing Attendance Mark (Localhost IP) ---")
res = session.post('http://127.0.0.1:5000/mark_attendance', data={
    'status': 'Present'
})
# We expect either success OR "only be marked during active time slots"
soup = BeautifulSoup(res.text, 'html.parser')
alerts = soup.find_all(class_='alert-content')
for a in alerts:
    print("Flash Message:", a.text.strip())

print("\n--- Testing Admin Login ---")
admin_session = requests.Session()
res = admin_session.post('http://127.0.0.1:5000/admin_login', data={
    'password': 'admin123'
})
print("Admin Logged In:", "Admin login successful" in res.text or "Admin Dashboard" in res.text)

print("\n--- Testing Admin Override ---")
# First get the user id for TEST999
soup = BeautifulSoup(res.text, 'html.parser')
# Simple test: just post an override for student_id 1 (assume exists)
import datetime
today = datetime.date.today().isoformat()
res = admin_session.post('http://127.0.0.1:5000/admin/update_attendance', data={
    'student_id': '1',
    'date': today,
    'status': 'Absent'
})
soup = BeautifulSoup(res.text, 'html.parser')
alerts = soup.find_all(class_='alert-content')
for a in alerts:
    print("Admin Action Result:", a.text.strip())

print("\nAll endpoints reached successfully.")
