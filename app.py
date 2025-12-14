import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from datetime import datetime
import pytz
import database  # type: ignore
import os
import base64
import qrcode  # type: ignore
from flask import session, make_response ## 1:30

app = Flask(__name__)## 1:30
app.secret_key = "your_secret_key"  # REQUIRED for session :130

# Ensure static directories exist
os.makedirs('static/photos', exist_ok=True)
os.makedirs('static/qr_codes', exist_ok=True)

# Initialize database on startup
database.init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/student/update/<student_id>", methods=["POST"])
def update_student_route(student_id):
    data = request.get_json()
    firstname = data.get("firstname")
    lastname = data.get("lastname")
    course = data.get("course")
    level = data.get("level")

    if not all([firstname, lastname, course, level]):
        return jsonify({"success": False, "message": "All fields are required"}), 400

    success, error_msg = database.update_student(student_id, firstname, lastname, course, level)
    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "message": error_msg or "Failed to update student"}), 400



@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    # Clear previous login session
    session.pop("admin_logged", None)

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        admin = database.verify_admin(email, password)
        if admin:
            session["admin_logged"] = True
            return redirect(url_for("admin_dashboard"))
        else:
            return render_template("admin_login.html", error="Invalid email or password")

    # Disable caching so Back button doesn't show dashboard
    response = make_response(render_template("admin_login.html"))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if not all([email, password, confirm_password]):
            return render_template("admin_register.html", error="All fields are required")
        
        if password != confirm_password:
            return render_template("admin_register.html", error="Passwords do not match")
        
        if len(password) < 6:
            return render_template("admin_register.html", error="Password must be at least 6 characters")
        
        name = email.split('@')[0]
        success, error_msg = database.add_admin(email, password, name)
        
        if success:
            # Redirect to login page after successful registration
            return redirect(url_for("admin_login"))
        else:
            return render_template("admin_register.html", error=error_msg or "Registration failed")
    
    return render_template("admin_register.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    nav_items = [
        {"label": "USER MANAGEMENT", "endpoint": "admin_dashboard"},
        {"label": "STUDENT MANAGMENT", "endpoint": "admin_students"},
        {"label": "ATTENDANCE", "endpoint": "admin_attendance"},
        {"label": "LOGOUT", "endpoint": "home"},
    ]

    all_admins = database.get_all_admins()
    users = []
    for admin in all_admins:
        users.append({
            "id": admin["id"],
            "name": admin["name"],
            "email": admin["email"],
            "password": "********"
        })

    response = make_response(render_template(
        "admin_page.html",
        nav_items=nav_items,
        users=users,
        active_endpoint="admin_dashboard",
    ))

    # Disable browser caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response

    
@app.route("/admin/students")##
def admin_students():
    # Redirect to login if not logged in
    if not session.get("admin_logged"):
        return redirect(url_for("admin_login"))

    nav_items = [
        {"label": "USER MANAGEMENT", "endpoint": "admin_dashboard"},
        {"label": "STUDENT MANAGEMENT", "endpoint": "admin_students"},
        {"label": "ATTENDANCE", "endpoint": "admin_attendance"},
        {"label": "LOGOUT", "endpoint": "home"},
    ]
    
    # Get all students from database
    all_students = database.get_all_students()
    
    # Format students for template
    students = []
    for student in all_students:
        students.append({
            "id": student["id"],
            "last": student["lastname"],
            "first": student["firstname"],
            "course": student["course"],
            "level": student["level"]
        })
    
    # Default student profile
    student_profile = {
        "id": students[0]["id"] if students else "0001",
        "name": f"{students[0]['last']}, {students[0]['first']}" if students else "sample, user",
        "course": f"{students[0]['course']}-{students[0]['level']}" if students else "BSIT-3",
    }
    
    return render_template(
        "student_mngt.html",
        nav_items=nav_items,
        active_endpoint="admin_students",
        student_profile=student_profile,
        students=students,
    )


@app.route("/admin/attendance", methods=["GET", "POST"])
def admin_attendance():
    nav_items = [
        {"label": "USER MANAGEMENTT", "endpoint": "admin_dashboard"},
        {"label": "STUDENT MANAGMENT", "endpoint": "admin_students"},
        {"label": "ATTENDANCE", "endpoint": "admin_attendance"},
        {"label": "LOGOUT", "endpoint": "home"},
    ]
    
    # Get date from request (default to today)
    selected_date = request.args.get('date') or request.form.get('date')
    if not selected_date:
        selected_date = datetime.now().strftime("%Y-%m-%d")
    
    # Get attendance records for the selected date
    attendance = database.get_attendance_by_date(selected_date)

    # 👉 SORT HERE (earliest time-in first)
    
    try:
        attendance = sorted(
            attendance,
            key=lambda x: datetime.strptime(x["time_in"], "%I:%M %p")
        )
    except:
        pass  # In case format differs, avoid crash

    return render_template(
        "view_attendance.html",
        nav_items=nav_items,
        active_endpoint="admin_attendance",
        attendance=attendance,
        selected_date=selected_date,
    )


@app.route("/student")
def student():
    return render_template("student.html")  

@app.route("/admin/logout")
def admin_logout():
    # Clear the login session
    session.pop("admin_logged", None)
    
    # Redirect to login page
    response = make_response(redirect(url_for("admin_login")))
    
    # Disable caching to prevent Back button from showing dashboard
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route("/api/attendance/delete/<int:attendance_id>", methods=["DELETE", "POST"])
def delete_attendance_api(attendance_id):
    """API endpoint to delete an attendance record"""
    # Check if admin is logged in
    if not session.get("admin_logged"):
        return jsonify({
            'success': False,
            'message': 'Unauthorized'
        }), 401
    
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM attendance WHERE id = ?', (attendance_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        if deleted:
            return jsonify({
                'success': True,
                'message': 'Attendance record deleted successfully'
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': 'Attendance record not found'
            }), 404
            
    except Exception as e:
        print(f"Error deleting attendance: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    

@app.route("/admin_page")
def admin_page():
    return render_template("admin_page.html")

@app.route("/api/admin/add", methods=["POST"])
def add_admin_api():
    """API endpoint to add a new admin user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', email.split('@')[0])  # Default name from email
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        success, error_msg = database.add_admin(email, password, name)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Admin user added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': error_msg or 'Failed to add admin user'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/admin/update/<int:admin_id>", methods=["PUT", "POST"])
def update_admin_api(admin_id):
    """API endpoint to update an admin user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name', email.split('@')[0] if email else None)  # Default name from email if not provided
        
        if not email or not password:  # Only require email and password
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        success, error_msg = database.update_admin(admin_id, email, password, name)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Admin user updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': error_msg or 'Failed to update admin user'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/admin/delete/<int:admin_id>", methods=["DELETE", "POST"])
def delete_admin_api(admin_id):
    """API endpoint to delete an admin user"""
    try:
        success, error_msg = database.delete_admin(admin_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Admin user deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': error_msg or 'Failed to delete admin user'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/admin/get/<int:admin_id>", methods=["GET"])
def get_admin_api(admin_id):
    """API endpoint to get an admin user by ID"""
    try:
        admin = database.get_admin_by_id(admin_id)
        
        if admin:
            return jsonify({
                'success': True,
                'admin': {
                    'id': admin['id'],
                    'email': admin['email'],
                    'password': admin['password'],
                    'name': admin['name']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Admin not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/student/generate-id", methods=["GET"])
def generate_student_id():
    """API endpoint to generate a unique student ID"""
    try:
        student_id = database.generate_unique_student_id()
        if student_id:
            return jsonify({
                'success': True,
                'student_id': student_id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to generate student ID'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/student/add", methods=["POST"])
def add_student_api():
    """API endpoint to add a new student"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        lastname = data.get('lastname')
        firstname = data.get('firstname')
        course = data.get('course')
        level = data.get('level')
        photo_base64 = data.get('photo')  # Base64 encoded image
        
        if not all([student_id, lastname, firstname, course, level]):
            return jsonify({
                'success': False,
                'message': 'All fields are required'
            }), 400
        
        # Save photo to file
        photo_path = None
        if photo_base64:
            try:
                # Remove data URL prefix if present
                if ',' in photo_base64:
                    photo_base64 = photo_base64.split(',')[1]
                
                photo_data = base64.b64decode(photo_base64)
                photo_filename = f"{student_id}_photo.png"
                photo_path = f"static/photos/{photo_filename}"
                
                with open(photo_path, 'wb') as f:
                    f.write(photo_data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'Error saving photo: {str(e)}'
                }), 400
        
        # Generate and save QR code
        qr_path = None
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(student_id)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_filename = f"{student_id}_qr.png"
            qr_path = f"static/qr_codes/{qr_filename}"
            qr_img.save(qr_path)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Error generating QR code: {str(e)}'
            }), 400
        
        # Save to database with file paths
        success, error_msg = database.add_student(student_id, lastname, firstname, course, level, photo_path, qr_path)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Student added successfully',
                'student_id': student_id,
                'photo_path': photo_path,
                'qr_path': qr_path
            })
        else:
            # Clean up files if database save failed
            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)
            if qr_path and os.path.exists(qr_path):
                os.remove(qr_path)
            return jsonify({
                'success': False,
                'message': error_msg or 'Failed to add student'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/student/get/<student_id>", methods=["GET"])
def get_student_api(student_id):
    """API endpoint to get a student by ID"""
    try:
        student = database.get_student(student_id)
        
        if student:
            return jsonify({
                'success': True,
                'student': dict(student)
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/student/delete/<student_id>", methods=["DELETE", "POST"])
def delete_student_api(student_id):
    """API endpoint to delete a student"""
    try:
        conn = database.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        if deleted:
            return jsonify({
                'success': True,
                'message': 'Student deleted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Student not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route("/api/scan-attendance", methods=["POST"])
def scan_attendance():
    """API endpoint to record attendance from QR code scan"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        if not student_id:
            return jsonify({
                'success': False,
                'message': 'Student ID is required'
            }), 400
        
        # Record attendance
        attendance_data, message = database.record_attendance(student_id)
        
        if attendance_data and isinstance(attendance_data, dict) and 'student_id' in attendance_data:
            # Success - attendance recorded
            return jsonify({
                'success': True,
                'message': message,
                'attendance': {
                    'time_in': attendance_data.get('time_in'),
                    'date': attendance_data.get('date')
                },
                'student': {
                    'id': attendance_data.get('student_id'),
                    'firstname': attendance_data.get('firstname'),
                    'lastname': attendance_data.get('lastname'),
                    'course': attendance_data.get('course'),
                    'level': attendance_data.get('level')
                }
            })
        else:
            # Error - student not found or already recorded
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
    
@app.route('/static/check_user')
def check_user():
    profile = {
        'id': request.args.get('id'),
        'firstname': request.args.get('firstname'),
        'lastname': request.args.get('lastname'),
        'course': request.args.get('course'),
        'level': request.args.get('level'),
    }
    return render_template('check_user.html', profile=profile)

# Route to serve static files (photos and QR codes)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route("/admin/delete_future_attendance")
def delete_future_attendance():
    import os
    # Ensure we are connecting to the correct database
    db_path = os.path.join(os.path.dirname(__file__), 'attendance.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM attendance WHERE date > DATE('now', 'localtime')")
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    
    return f"{deleted} future attendance entries deleted."


if __name__ == "__main__":
    app.run(debug=True)