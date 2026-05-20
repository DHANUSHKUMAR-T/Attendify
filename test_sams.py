import unittest
from datetime import datetime, time, date
import sqlite3
import os
from app import app, get_db, init_db, ADMIN_PASSWORD

class SAMSTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Use an in-memory DB for testing or a separate file
        self.db_fd = "test_attendance.db"
        app.config['DB_PATH'] = self.db_fd
        
        # Override get_db locally for testing if needed
        # But app.py uses DB_PATH globally. Let's just create a test db
        with app.app_context():
            # init_db creates tables
            init_db()
        self.client = app.test_client()

    def tearDown(self):
        if os.path.exists(self.db_fd):
            pass # os.remove(self.db_fd) # clean up if needed

    def register_test_user(self):
        return self.client.post('/register', data=dict(
            register_number='TEST001',
            name='Test User',
            course='DCA',
            mobile='1234567890',
            password='password123',
            confirm_password='password123'
        ), follow_redirects=True)

    def login_test_user(self):
        return self.client.post('/login', data=dict(
            register_number='TEST001',
            password='password123'
        ), follow_redirects=True)

    def test_registration_and_login(self):
        # Test Registration
        rv = self.register_test_user()
        self.assertIn(b'Registration successful', rv.data)
        
        # Test Login
        rv = self.login_test_user()
        self.assertIn(b'Welcome back', rv.data)

    # Note: Testing time and IP requires mocking request remote_addr and datetime,
    # which is easier done interactively. I will use a simple script to test this.

if __name__ == '__main__':
    unittest.main()
