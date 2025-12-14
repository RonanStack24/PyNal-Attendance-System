import sqlite3
from datetime import datetime
import os

DB_NAME = "attendance.db"



def update_student(student_id, firstname, lastname, course, level):
    """Update a student's name and course-level"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE students
            SET firstname = ?, lastname = ?, course = ?, level = ?
            WHERE id = ?
        ''', (firstname, lastname, course, level, student_id))
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated, None if updated else "Student not found"
    except Exception as e:
        conn.close()
        return False, str(e)


def get_db_connection():
    """Create and return a database connection"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            lastname TEXT NOT NULL,
            firstname TEXT NOT NULL,
            course TEXT NOT NULL,
            level TEXT NOT NULL,
            photo TEXT,
            qr_code TEXT
        )
    ''')
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            date TEXT NOT NULL,
            time_in TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    ''')
    
    # Create admin table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database '{DB_NAME}' initialized successfully!")

def generate_unique_student_id():
    """Generate a unique 4-digit student ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Start from 0001 and find the next available ID
    for i in range(1, 10000):
        student_id = f"{i:04d}"  # Format as 4-digit string (0001, 0002, etc.)
        cursor.execute('SELECT id FROM students WHERE id = ?', (student_id,))
        if not cursor.fetchone():
            conn.close()
            return student_id
    
    conn.close()
    return None  # Should never reach here

def add_student(student_id, lastname, firstname, course, level, photo_path=None, qr_code_path=None):
    """Add a new student to the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO students (id, lastname, firstname, course, level, photo, qr_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, lastname, firstname, course, level, photo_path, qr_code_path))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        # Student already exists
        return False, "Student ID already exists"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_student(student_id):
    """Get student information by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    return dict(student) if student else None

import pytz
from datetime import datetime

def record_attendance(student_id):
    """Record attendance for a student"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if student exists
    student = get_student(student_id)
    if not student:
        conn.close()
        return None, "Student not found"
    
    # Get current date and time in PH timezone
    ph_time = datetime.now(pytz.timezone("Asia/Manila"))
    date = ph_time.strftime("%Y-%m-%d")
    time_in = ph_time.strftime("%I:%M %p")
    
    # Check if attendance already recorded for today
    cursor.execute('''
        SELECT * FROM attendance 
        WHERE student_id = ? AND date = ?
    ''', (student_id, date))
    
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return dict(existing), "Attendance already recorded for today"
    
    # Record new attendance
    cursor.execute('''
        INSERT INTO attendance (student_id, date, time_in)
        VALUES (?, ?, ?)
    ''', (student_id, date, time_in))
    
    conn.commit()
    conn.close()
    
    return {
        'student_id': student_id,
        'date': date,
        'time_in': time_in,
        'lastname': student['lastname'],
        'firstname': student['firstname'],
        'course': student['course'],
        'level': student['level']
    }, "Attendance recorded successfully"


def get_attendance_by_date(date):
    """Get all attendance records for a specific date"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            a.id,
            s.id as student_id,
            s.lastname as last,
            s.firstname as first,
            s.course,
            s.level,
            a.time_in
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.date = ?
        ORDER BY a.time_in
    ''', (date,))
    
    records = cursor.fetchall()
    conn.close()
    
    return [dict(record) for record in records]

def get_all_attendance():
    """Get all attendance records"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            a.id,
            s.id as student_id,
            s.lastname as last,
            s.firstname as first,
            s.course,
            s.level,
            a.date,
            a.time_in
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        ORDER BY a.date DESC, a.time_in DESC
    ''')
    
    records = cursor.fetchall()
    conn.close()
    
    return [dict(record) for record in records]

def get_all_students():
    """Get all students from the database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM students ORDER BY id')
    students = cursor.fetchall()
    conn.close()
    
    return [dict(student) for student in students]

def verify_admin(email, password):
    """Verify admin login credentials"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM admin WHERE email = ? AND password = ?', (email, password))
    admin = cursor.fetchone()
    conn.close()
    
    return dict(admin) if admin else None

def add_admin(email, password, name):
    """Add a new admin user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO admin (email, password, name)
            VALUES (?, ?, ?)
        ''', (email, password, name))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        # Admin already exists
        return False, "Email already exists"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_all_admins():
    """Get all admin users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM admin ORDER BY id')
    admins = cursor.fetchall()
    conn.close()
    
    return [dict(admin) for admin in admins]

def get_admin_by_id(admin_id):
    """Get admin by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM admin WHERE id = ?', (admin_id,))
    admin = cursor.fetchone()
    conn.close()
    
    return dict(admin) if admin else None

def update_admin(admin_id, email, password, name):
    """Update an admin user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if email is being changed and if it already exists
        cursor.execute('SELECT * FROM admin WHERE id = ?', (admin_id,))
        current_admin = cursor.fetchone()
        
        if not current_admin:
            conn.close()
            return False, "Admin not found"
        
        # Check if email is taken by another admin
        cursor.execute('SELECT * FROM admin WHERE email = ? AND id != ?', (email, admin_id))
        if cursor.fetchone():
            conn.close()
            return False, "Email already exists"
        
        # Update admin
        cursor.execute('''
            UPDATE admin 
            SET email = ?, password = ?, name = ?
            WHERE id = ?
        ''', (email, password, name, admin_id))
        conn.commit()
        conn.close()
        return True, None
    except Exception as e:
        conn.close()
        return False, str(e)

def delete_admin(admin_id):
    """Delete an admin user"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM admin WHERE id = ?', (admin_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted, None if deleted else "Admin not found"
    except Exception as e:
        conn.close()
        return False, str(e)

def add_sample_data():
    """Add sample students and attendance data for testing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sample students
    sample_students = [
        ("0001", "Durano", "Dennis", "BSCPE", "3", None, None),
        ("0002", "Badilles", "Govan", "BSIT", "2", None, None),
        ("0003", "Ronan", "Antoque", "BSIT", "3", None, None),
        ("0004", "Libradilla", "Cedrick", "BSCRIM", "3", None, None),
    ]
    
    for student in sample_students:
        try:
            add_student(*student)
        except:
            pass  # Student might already exist
    
    # Sample admin account
    try:
        add_admin("admin@test.com", "admin123", "Admin User")
    except:
        pass  # Admin might already exist
    
    conn.close()
    print("Sample data added!")

if __name__ == "__main__":
    # Initialize database when run directly
    init_db()
    add_sample_data()

