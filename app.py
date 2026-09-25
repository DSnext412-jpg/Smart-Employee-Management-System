from flask import Flask, render_template, jsonify, request, session, redirect, url_for, abort, flash
from dotenv import load_dotenv
import os
import MySQLdb
from MySQLdb.cursors import DictCursor
import re

from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT, SECRET_KEY, DEBUG

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["DEBUG"] = DEBUG
app.config["MYSQL_HOST"] = MYSQL_HOST
app.config["MYSQL_USER"] = MYSQL_USER
app.config["MYSQL_PASSWORD"] = MYSQL_PASSWORD
app.config["MYSQL_DB"] = MYSQL_DB
app.config["MYSQL_PORT"] = MYSQL_PORT


def get_db_connection():
    return MySQLdb.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        passwd=app.config["MYSQL_PASSWORD"],
        db=app.config["MYSQL_DB"],
        port=app.config["MYSQL_PORT"],
        cursorclass=DictCursor,
    )


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/", methods=["GET"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            return render_template(
                "login.html",
                error="Username and password are required.",
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, username, email, password, role FROM users WHERE username = %s OR email = %s",
            (username, username),
        )
        user = cursor.fetchone()
        conn.close()

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "login.html",
                error="Invalid username or password.",
            )

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM employees")
    total_employees = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM departments")
    total_departments = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM attendance WHERE date = CURDATE()")
    today_attendance = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(*) AS count FROM leaves WHERE status = 'pending'")
    pending_leaves = cursor.fetchone()["count"]

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_employees=total_employees,
        total_departments=total_departments,
        today_attendance=today_attendance,
        pending_leaves=pending_leaves
    )


@app.route("/employees")
@login_required
def employees():
    search_term = request.args.get('search', '')
    conn = get_db_connection()
    cursor = conn.cursor()

    if search_term:
        like_term = f"%{search_term}%"
        cursor.execute("""
            SELECT
                e.id,
                e.employee_id,
                e.first_name,
                e.last_name,
                e.email,
                e.phone,
                e.position,
                d.name AS department_name,
                e.status
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE
                e.employee_id LIKE %s
                OR e.first_name LIKE %s
                OR e.last_name LIKE %s
                OR e.email LIKE %s
                OR e.position LIKE %s
            ORDER BY e.id DESC
        """, (like_term, like_term, like_term, like_term, like_term))
    else:
        cursor.execute("""
            SELECT
                e.id,
                e.employee_id,
                e.first_name,
                e.last_name,
                e.email,
                e.phone,
                e.position,
                d.name AS department_name,
                e.status
            FROM employees e
            LEFT JOIN departments d ON e.department_id = d.id
            ORDER BY e.id DESC
        """)

    employees = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("employees.html", employees=employees, search_term=search_term)


@app.route("/employees/add")
@login_required
def employees_add():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("employee_form.html", employee_form_title="Add Employee", departments=departments)


@app.route("/employees/add", methods=["POST"])
@login_required
def employees_add_post():
    employee_id = request.form.get('employee_id', '').strip()
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    gender = request.form.get('gender', '').strip()
    date_of_birth = request.form.get('date_of_birth', '').strip()
    address = request.form.get('address', '').strip()
    position = request.form.get('position', '').strip()
    salary = request.form.get('salary', '').strip()
    hire_date = request.form.get('hire_date', '').strip()
    department_id = request.form.get('department_id', '').strip()
    status = request.form.get('status', '').strip()

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee ID is required.'
    if not first_name:
        validation_errors['first_name'] = 'First Name is required.'
    if not last_name:
        validation_errors['last_name'] = 'Last Name is required.'
    if not email:
        validation_errors['email'] = 'Email is required.'
    if not position:
        validation_errors['position'] = 'Position is required.'
    if not hire_date:
        validation_errors['hire_date'] = 'Hire Date is required.'
    if not department_id:
        validation_errors['department_id'] = 'Department is required.'

    if email and '@' not in email:
        validation_errors['email'] = 'Please enter a valid email address.'

    if date_of_birth:
        try:
            from datetime import datetime
            datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            validation_errors['date_of_birth'] = 'Invalid date format.'

    if hire_date:
        try:
            from datetime import datetime
            datetime.strptime(hire_date, '%Y-%m-%d')
        except ValueError:
            validation_errors['hire_date'] = 'Invalid date format.'

    if employee_id and not validation_errors.get('employee_id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE employee_id = %s", (employee_id,))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            validation_errors['employee_id'] = 'Employee ID already exists.'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        departments = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            "employee_form.html",
            employee_form_title="Add Employee",
            departments=departments,
            validation_errors=validation_errors,
            employee_employee_id=employee_id,
            employee_first_name=first_name,
            employee_last_name=last_name,
            employee_email=email,
            employee_phone=phone,
            employee_gender=gender,
            employee_dob=date_of_birth,
            employee_address=address,
            employee_position=position,
            employee_salary=salary,
            employee_hire_date=hire_date,
            employee_department_id=department_id,
            employee_status=status
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO employees (
            employee_id, first_name, last_name, email, phone, gender,
            date_of_birth, address, position, salary, hire_date, department_id, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (employee_id, first_name, last_name, email, phone, gender,
          date_of_birth, address, position, salary, hire_date, department_id, status))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Employee added successfully.')
    return redirect(url_for('employees'))


@app.route("/employees/<int:id>")
@login_required
def employee_details(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            e.id,
            e.employee_id,
            e.first_name,
            e.last_name,
            e.email,
            e.phone,
            e.gender,
            e.date_of_birth,
            e.address,
            e.position,
            e.salary,
            e.hire_date,
            d.name AS department_name,
            e.status
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.id = %s
    """, (id,))
    employee = cursor.fetchone()
    cursor.close()
    conn.close()

    if not employee:
        abort(404)

    return render_template("employee_details.html", employee=employee)


@app.route("/employees/<int:id>/edit")
@login_required
def employee_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            e.id,
            e.employee_id,
            e.first_name,
            e.last_name,
            e.email,
            e.phone,
            e.gender,
            e.date_of_birth,
            e.address,
            e.position,
            e.salary,
            e.hire_date,
            e.department_id,
            e.status
        FROM employees e
        WHERE e.id = %s
    """, (id,))
    employee = cursor.fetchone()

    if not employee:
        cursor.close()
        conn.close()
        abort(404)

    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("employee_form.html",
                         employee_form_title="Edit Employee",
                         employee=employee,
                         departments=departments,
                         employee_id=employee['id'],
                         employee_employee_id=employee['employee_id'],
                         employee_first_name=employee['first_name'],
                         employee_last_name=employee['last_name'],
                         employee_email=employee['email'],
                         employee_phone=employee['phone'],
                         employee_gender=employee['gender'],
                         employee_dob=employee['date_of_birth'],
                         employee_address=employee['address'],
                         employee_position=employee['position'],
                         employee_salary=employee['salary'],
                         employee_hire_date=employee['hire_date'],
                         employee_department_id=employee['department_id'],
                         employee_status=employee['status'])


@app.route("/employees/<int:id>/edit", methods=["POST"])
@login_required
def employee_edit_post(id):
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    gender = request.form.get('gender', '').strip()
    date_of_birth = request.form.get('date_of_birth', '').strip()
    address = request.form.get('address', '').strip()
    position = request.form.get('position', '').strip()
    salary = request.form.get('salary', '').strip()
    department_id = request.form.get('department_id', '').strip()
    status = request.form.get('status', '').strip()
    employee_id = request.form.get('employee_id', '').strip()
    hire_date = request.form.get('hire_date', '').strip()

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee ID is required.'

    if email and '@' not in email:
        validation_errors['email'] = 'Please enter a valid email address.'

    if date_of_birth:
        try:
            from datetime import datetime
            datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            validation_errors['date_of_birth'] = 'Invalid date format.'

    if hire_date:
        try:
            from datetime import datetime
            datetime.strptime(hire_date, '%Y-%m-%d')
        except ValueError:
            validation_errors['hire_date'] = 'Invalid date format.'

    if not first_name:
        validation_errors['first_name'] = 'First Name is required.'
    if not last_name:
        validation_errors['last_name'] = 'Last Name is required.'
    if not email:
        validation_errors['email'] = 'Email is required.'
    if not position:
        validation_errors['position'] = 'Position is required.'
    if not hire_date:
        validation_errors['hire_date'] = 'Hire Date is required.'
    if not department_id:
        validation_errors['department_id'] = 'Department is required.'

    if employee_id and not validation_errors.get('employee_id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE employee_id = %s AND id != %s",
                       (employee_id, id))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            validation_errors['employee_id'] = 'Employee ID already exists.'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM departments ORDER BY name")
        departments = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            "employee_form.html",
            employee_form_title="Edit Employee",
            departments=departments,
            validation_errors=validation_errors,
            employee_id=id,
            employee_employee_id=employee_id,
            employee_first_name=first_name,
            employee_last_name=last_name,
            employee_email=email,
            employee_phone=phone,
            employee_gender=gender,
            employee_dob=date_of_birth,
            employee_address=address,
            employee_position=position,
            employee_salary=salary,
            employee_hire_date=hire_date,
            employee_department_id=department_id,
            employee_status=status
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE employees
        SET employee_id = %s, first_name = %s, last_name = %s, email = %s, phone = %s, gender = %s,
            date_of_birth = %s, address = %s, position = %s, salary = %s, hire_date = %s,
            department_id = %s, status = %s
        WHERE id = %s
    """, (employee_id, first_name, last_name, email, phone, gender,
          date_of_birth, address, position, salary, hire_date, department_id, status, id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Employee updated successfully.')
    return redirect(url_for('employee_details', id=id))


@app.route("/employees/<int:id>/delete", methods=["POST"])
@login_required
def employee_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM employees WHERE id = %s", (id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM employees WHERE id = %s", (id,))
        conn.commit()
        flash('Employee deleted successfully.')

    cursor.close()
    conn.close()

    return redirect(url_for('employees'))


@app.route("/departments")
@login_required
def departments():
    search_term = request.args.get('search', '')
    conn = get_db_connection()
    cursor = conn.cursor()

    if search_term:
        like_term = f"%{search_term}%"
        cursor.execute("""
            SELECT
                d.id,
                d.name,
                d.description,
                COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e ON d.id = e.department_id
            WHERE LOWER(d.name) LIKE LOWER(%s) OR LOWER(d.description) LIKE LOWER(%s)
            GROUP BY d.id, d.name, d.description
            ORDER BY d.name
        """, (like_term, like_term))
    else:
        cursor.execute("""
            SELECT
                d.id,
                d.name,
                d.description,
                COUNT(e.id) AS employee_count
            FROM departments d
            LEFT JOIN employees e ON d.id = e.department_id
            GROUP BY d.id, d.name, d.description
            ORDER BY d.name
        """)

    departments = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("departments.html", departments=departments, search_term=search_term)


@app.route("/departments/add")
@login_required
def departments_add():
    return render_template("department_form.html", department_form_title="Add Department")


@app.route("/departments/add", methods=["POST"])
@login_required
def departments_add_post():
    department_name = request.form.get('department_name', '').strip()
    department_description = request.form.get('department_description', '').strip()

    validation_errors = {}

    if not department_name:
        validation_errors['name'] = 'Department name is required.'

    if department_name and not validation_errors.get('name'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM departments WHERE LOWER(name) = LOWER(%s)", (department_name,))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            validation_errors['name'] = 'Department name already exists.'

    if validation_errors:
        return render_template(
            "department_form.html",
            department_form_title="Add Department",
            validation_errors=validation_errors,
            department_name=department_name,
            department_description=department_description
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO departments (name, description) VALUES (%s, %s)",
                   (department_name, department_description))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Department added successfully.')
    return redirect(url_for('departments'))


@app.route("/departments/<int:id>")
@login_required
def department_details(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            d.id,
            d.name,
            d.description,
            d.created_at,
            COUNT(e.id) AS employee_count
        FROM departments d
        LEFT JOIN employees e
            ON d.id = e.department_id
        WHERE d.id = %s
        GROUP BY d.id, d.name, d.description, d.created_at
    """, (id,))
    department = cursor.fetchone()

    if not department:
        cursor.close()
        conn.close()
        abort(404)

    cursor.execute("""
        SELECT
            e.employee_id,
            e.first_name,
            e.last_name,
            e.position,
            e.status
        FROM employees e
        WHERE e.department_id = %s
        ORDER BY e.first_name, e.last_name
    """, (id,))
    employees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("department_details.html", department=department, employees=employees)


@app.route("/departments/<int:id>/edit")
@login_required
def departments_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments WHERE id = %s", (id,))
    department = cursor.fetchone()

    if not department:
        cursor.close()
        conn.close()
        abort(404)

    cursor.close()
    conn.close()

    return render_template("department_form.html",
                         department_form_title="Edit Department",
                         department=department,
                         department_id=department['id'],
                         department_name=department['name'],
                         department_description=department['description'])


@app.route("/departments/<int:id>/edit", methods=["POST"])
@login_required
def departments_edit_post(id):
    department_name = request.form.get('department_name', '').strip()
    department_description = request.form.get('department_description', '').strip()

    validation_errors = {}

    if not department_name:
        validation_errors['name'] = 'Department name is required.'

    if department_name and not validation_errors.get('name'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM departments WHERE LOWER(name) = LOWER(%s) AND id != %s",
                       (department_name, id))
        existing = cursor.fetchone()
        conn.close()

        if existing:
            validation_errors['name'] = 'Department name already exists.'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM departments WHERE id = %s", (id,))
        department = cursor.fetchone()
        cursor.close()
        conn.close()

        if not department:
            abort(404)

        return render_template(
            "department_form.html",
            department_form_title="Edit Department",
            department=department,
            department_id=id,
            validation_errors=validation_errors,
            department_name=department_name,
            department_description=department_description
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE departments SET name = %s, description = %s WHERE id = %s",
                   (department_name, department_description, id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Department updated successfully.')
    return redirect(url_for('departments'))


@app.route("/departments/<int:id>/delete", methods=["POST"])
@login_required
def departments_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM departments WHERE id = %s", (id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM departments WHERE id = %s", (id,))
        conn.commit()
        flash('Department deleted successfully.')
    else:
        flash('Department not found.')

    cursor.close()
    conn.close()

    return redirect(url_for('departments'))


@app.route("/attendance")
@login_required
def attendance():
    search_term = request.args.get('search', '')
    employee_id_filter = request.args.get('employee_id', '')
    date_filter = request.args.get('date', '')
    status_filter = request.args.get('status', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            a.id,
            a.employee_id,
            e.employee_id AS employee_code,
            e.first_name,
            e.last_name,
            a.date,
            a.check_in,
            a.check_out,
            a.status,
            a.created_at
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
    """
    params = []
    where_added = False

    if search_term:
        query += " WHERE (e.employee_id LIKE %s OR e.first_name LIKE %s OR e.last_name LIKE %s)"
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term, like_term])
        where_added = True

    if employee_id_filter:
        if where_added:
            query += " AND a.employee_id = %s"
        else:
            query += " WHERE a.employee_id = %s"
        params.append(employee_id_filter)
        where_added = True

    if date_filter:
        if where_added:
            query += " AND a.date = %s"
        else:
            query += " WHERE a.date = %s"
        params.append(date_filter)
        where_added = True

    if status_filter:
        if where_added:
            query += " AND a.status = %s"
        else:
            query += " WHERE a.status = %s"
        params.append(status_filter)
        where_added = True

    query += " ORDER BY a.date DESC, e.first_name, e.last_name"

    cursor.execute(query, params)
    attendance_records = cursor.fetchall()

    cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
    employees = cursor.fetchall()

    cursor.execute("SELECT DISTINCT status FROM attendance")
    statuses = [row['status'] for row in cursor.fetchall()]

    cursor.execute("SELECT status, COUNT(*) AS count FROM attendance GROUP BY status")
    attendance_summary = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "attendance.html",
        attendance=attendance_records,
        employees=employees,
        search_term=search_term or '',
        employee_id_filter=employee_id_filter,
        date_filter=date_filter,
        status_filter=status_filter,
        statuses=statuses or [],
        attendance_summary=attendance_summary or []
    )


@app.route("/attendance/add")
@login_required
def attendance_add():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("attendance_form.html", action="/attendance/add", employees=employees, attendance=None)


@app.route("/attendance/add", methods=["POST"])
@login_required
def attendance_add_post():
    employee_id = request.form.get('employee_id', '').strip()
    date = request.form.get('date', '').strip()
    check_in = request.form.get('check_in', '').strip()
    check_out = request.form.get('check_out', '').strip()
    status = request.form.get('status', '').strip()

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee is required.'
    if not date:
        validation_errors['date'] = 'Date is required.'
    if not status:
        validation_errors['status'] = 'Status is required.'

    if employee_id and not validation_errors.get('employee_id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE id = %s", (employee_id,))
        existing = cursor.fetchone()
        conn.close()

        if not existing:
            validation_errors['employee_id'] = 'Employee does not exist.'

    if status and not validation_errors.get('status'):
        valid_statuses = ['present', 'absent', 'late', 'half day']
        if status.lower() not in [s.lower() for s in valid_statuses]:
            validation_errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'

    if check_in and not validation_errors.get('check_in'):
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)(:[0-5]\d)?$', check_in):
            validation_errors['check_in'] = 'Check-in must be a valid time (HH:MM or HH:MM:SS).'

    if check_out and not validation_errors.get('check_out'):
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)(:[0-5]\d)?$', check_out):
            validation_errors['check_out'] = 'Check-out must be a valid time (HH:MM or HH:MM:SS).'

    if date:
        try:
            from datetime import datetime
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            validation_errors['date'] = 'Invalid date format.'

    if not validation_errors.get('employee_id') and employee_id and not validation_errors.get('date') and date:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM attendance WHERE employee_id = %s AND date = %s",
            (employee_id, date)
        )
        duplicate = cursor.fetchone()
        conn.close()

        if duplicate:
            validation_errors['date'] = 'Attendance already exists for this employee on this date.'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            "attendance_form.html",
            action="/attendance/add",
            employees=employees,
            validation_errors=validation_errors,
            attendance={
                'employee_id': employee_id,
                'date': date,
                'check_in': check_in,
                'check_out': check_out,
                'status': status
            }
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO attendance (employee_id, date, check_in, check_out, status)
        VALUES (%s, %s, %s, %s, %s)
    """, (employee_id, date, check_in, check_out, status))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Attendance record added successfully.')
    return redirect(url_for('attendance'))


@app.route("/attendance/<int:id>")
@login_required
def attendance_details(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            a.id,
            a.date,
            a.check_in,
            a.check_out,
            a.status,
            e.employee_id AS employee_code,
            e.first_name,
            e.last_name,
            e.position,
            d.name AS department_name
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE a.id = %s
    """, (id,))
    attendance = cursor.fetchone()
    cursor.close()
    conn.close()

    if not attendance:
        abort(404)

    return render_template("attendance_details.html", attendance=attendance)


@app.route("/attendance/<int:id>/edit")
@login_required
def attendance_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE id = %s", (id,))
    attendance = cursor.fetchone()

    if not attendance:
        cursor.close()
        conn.close()
        abort(404)

    cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("attendance_form.html", action=f"/attendance/{id}/edit", employees=employees, attendance=attendance)


@app.route("/attendance/<int:id>/edit", methods=["POST"])
@login_required
def attendance_edit_post(id):
    employee_id = request.form.get('employee_id', '').strip()
    date = request.form.get('date', '').strip()
    check_in = request.form.get('check_in', '').strip()
    check_out = request.form.get('check_out', '').strip()
    status = request.form.get('status', '').strip()

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee is required.'
    if not date:
        validation_errors['date'] = 'Date is required.'
    if not status:
        validation_errors['status'] = 'Status is required.'

    if employee_id and not validation_errors.get('employee_id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE id = %s", (employee_id,))
        existing = cursor.fetchone()
        conn.close()

        if not existing:
            validation_errors['employee_id'] = 'Employee does not exist.'

    if status and not validation_errors.get('status'):
        valid_statuses = ['present', 'absent', 'late', 'half day']
        if status.lower() not in [s.lower() for s in valid_statuses]:
            validation_errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'

    if check_in and not validation_errors.get('check_in'):
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)(:[0-5]\d)?$', check_in):
            validation_errors['check_in'] = 'Check-in must be a valid time (HH:MM or HH:MM:SS).'

    if check_out and not validation_errors.get('check_out'):
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)(:[0-5]\d)?$', check_out):
            validation_errors['check_out'] = 'Check-out must be a valid time (HH:MM or HH:MM:SS).'

    if date:
        try:
            from datetime import datetime
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            validation_errors['date'] = 'Invalid date format.'

    if not validation_errors.get('employee_id') and employee_id and not validation_errors.get('date') and date:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM attendance WHERE employee_id = %s AND date = %s AND id != %s",
            (employee_id, date, id)
        )
        duplicate = cursor.fetchone()
        conn.close()

        if duplicate:
            validation_errors['date'] = 'Attendance already exists for this employee on this date.'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            "attendance_form.html",
            action=f"/attendance/{id}/edit",
            employees=employees,
            validation_errors=validation_errors,
            attendance={
                'employee_id': employee_id,
                'date': date,
                'check_in': check_in,
                'check_out': check_out,
                'status': status,
                'id': id
            }
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE attendance
        SET employee_id = %s, date = %s, check_in = %s, check_out = %s, status = %s
        WHERE id = %s
    """, (employee_id, date, check_in, check_out, status, id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Attendance record updated successfully.')
    return redirect(url_for('attendance'))


@app.route("/attendance/<int:id>/delete", methods=["POST"])
@login_required
def attendance_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM attendance WHERE id = %s", (id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM attendance WHERE id = %s", (id,))
        conn.commit()
        flash('Attendance record deleted successfully.')

    cursor.close()
    conn.close()

    return redirect(url_for('attendance'))


@app.route("/leaves")
@login_required
def leaves():
    search_term = request.args.get('search', '')
    employee_id_filter = request.args.get('employee_id', '')
    leave_type_filter = request.args.get('leave_type', '')
    status_filter = request.args.get('status', '')
    start_date_filter = request.args.get('start_date', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            l.id,
            l.employee_id,
            e.employee_id AS employee_code,
            e.first_name,
            e.last_name,
            l.leave_type,
            l.start_date,
            l.end_date,
            l.reason,
            l.status,
            l.created_at
        FROM leaves l
        JOIN employees e ON l.employee_id = e.id
    """
    params = []
    where_added = False

    if search_term:
        query += " WHERE (e.employee_id LIKE %s OR e.first_name LIKE %s OR e.last_name LIKE %s)"
        like_term = f"%{search_term}%"
        params.extend([like_term, like_term, like_term])
        where_added = True

    if employee_id_filter:
        if where_added:
            query += " AND l.employee_id = %s"
        else:
            query += " WHERE l.employee_id = %s"
        params.append(employee_id_filter)
        where_added = True

    if leave_type_filter:
        if where_added:
            query += " AND l.leave_type = %s"
        else:
            query += " WHERE l.leave_type = %s"
        params.append(leave_type_filter)
        where_added = True

    if status_filter:
        if where_added:
            query += " AND l.status = %s"
        else:
            query += " WHERE l.status = %s"
        params.append(status_filter)
        where_added = True

    if start_date_filter:
        if where_added:
            query += " AND l.start_date = %s"
        else:
            query += " WHERE l.start_date = %s"
        params.append(start_date_filter)
        where_added = True

    query += " ORDER BY l.created_at DESC"

    cursor.execute(query, params)
    leaves_records = cursor.fetchall()

    cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
    employees = cursor.fetchall()

    cursor.execute("SELECT DISTINCT leave_type FROM leaves")
    leave_types = [row['leave_type'] for row in cursor.fetchall()]

    cursor.execute("SELECT DISTINCT status FROM leaves")
    statuses = [row['status'] for row in cursor.fetchall()]

    cursor.execute("SELECT status, COUNT(*) AS count FROM leaves GROUP BY status")
    leave_summary = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "leaves.html",
        leaves=leaves_records,
        employees=employees,
        search_term=search_term or '',
        employee_id_filter=employee_id_filter,
        leave_type_filter=leave_type_filter or '',
        status_filter=status_filter or '',
        start_date_filter=start_date_filter or '',
        leave_types=leave_types or [],
        statuses=statuses or [],
        leave_summary=leave_summary or []
    )


@app.route("/leaves/add")
@login_required
def leaves_add():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("leave_form.html", action="/leaves/add", employees=employees, leave=None)


@app.route("/leaves/add", methods=["POST"])
@login_required
def leaves_add_post():
    employee_id = request.form.get('employee_id', '').strip()
    leave_type = request.form.get('leave_type', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    reason = request.form.get('reason', '').strip()
    status = request.form.get('status', '').strip() or 'pending'

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee is required.'
    if not leave_type:
        validation_errors['leave_type'] = 'Leave type is required.'
    if not start_date:
        validation_errors['start_date'] = 'Start date is required.'
    if not end_date:
        validation_errors['end_date'] = 'End date is required.'
    if not status:
        validation_errors['status'] = 'Status is required.'

    if employee_id and not validation_errors.get('employee_id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE id = %s", (employee_id,))
        existing = cursor.fetchone()
        conn.close()

        if not existing:
            validation_errors['employee_id'] = 'Employee does not exist.'

    if start_date and end_date and not validation_errors.get('start_date') and not validation_errors.get('end_date'):
        if start_date > end_date:
            validation_errors['end_date'] = 'End date cannot be before start date.'

    if status and not validation_errors.get('status'):
        valid_statuses = ['pending', 'approved', 'rejected']
        if status.lower() not in [s.lower() for s in valid_statuses]:
            validation_errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'

    if not validation_errors.get('employee_id') and employee_id and start_date and not validation_errors.get('end_date') and end_date:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM leaves WHERE employee_id = %s AND start_date = %s AND end_date = %s",
            (employee_id, start_date, end_date)
        )
        duplicate = cursor.fetchone()
        conn.close()

        if duplicate:
            validation_errors['end_date'] = 'Leave already exists for this employee on this date range.'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            "leave_form.html",
            action="/leaves/add",
            employees=employees,
            validation_errors=validation_errors,
            leave={
                'employee_id': employee_id,
                'leave_type': leave_type,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason,
                'status': status
            }
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO leaves (employee_id, leave_type, start_date, end_date, reason, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (employee_id, leave_type, start_date, end_date, reason, status))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Leave added successfully.')
    return redirect(url_for('leaves'))


@app.route("/leaves/<int:id>")
@login_required
def leaves_details(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            l.id,
            l.employee_id,
            e.employee_id AS employee_code,
            e.first_name,
            e.last_name,
            l.leave_type,
            l.start_date,
            l.end_date,
            l.reason,
            l.status,
            l.created_at
        FROM leaves l
        JOIN employees e ON l.employee_id = e.id
        WHERE l.id = %s
    """, (id,))
    leave = cursor.fetchone()
    cursor.close()
    conn.close()

    if not leave:
        abort(404)

    return render_template("leave_details.html", leave=leave)


@app.route("/leaves/<int:id>/edit")
@login_required
def leaves_edit(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leaves WHERE id = %s", (id,))
    leave = cursor.fetchone()

    if not leave:
        cursor.close()
        conn.close()
        abort(404)

    cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("leave_form.html", action=f"/leaves/{id}/edit", employees=employees, leave=leave)


@app.route("/leaves/<int:id>/edit", methods=["POST"])
@login_required
def leaves_edit_post(id):
    employee_id = request.form.get('employee_id', '').strip()
    leave_type = request.form.get('leave_type', '').strip()
    start_date = request.form.get('start_date', '').strip()
    end_date = request.form.get('end_date', '').strip()
    reason = request.form.get('reason', '').strip()
    status = request.form.get('status', '').strip()

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee is required.'
    if not leave_type:
        validation_errors['leave_type'] = 'Leave type is required.'
    if not start_date:
        validation_errors['start_date'] = 'Start date is required.'
    if not end_date:
        validation_errors['end_date'] = 'End date is required.'
    if not status:
        validation_errors['status'] = 'Status is required.'

    if employee_id and not validation_errors.get('employee_id'):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM employees WHERE id = %s", (employee_id,))
        existing = cursor.fetchone()
        conn.close()

        if not existing:
            validation_errors['employee_id'] = 'Employee does not exist.'

    if start_date and end_date and not validation_errors.get('start_date') and not validation_errors.get('end_date'):
        if start_date > end_date:
            validation_errors['end_date'] = 'End date cannot be before start date.'

    if status and not validation_errors.get('status'):
        valid_statuses = ['pending', 'approved', 'rejected']
        if status.lower() not in [s.lower() for s in valid_statuses]:
            validation_errors['status'] = f'Status must be one of: {", ".join(valid_statuses)}'

    if validation_errors:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, employee_id, first_name, last_name FROM employees ORDER BY first_name, last_name")
        employees = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template(
            "leave_form.html",
            action=f"/leaves/{id}/edit",
            employees=employees,
            validation_errors=validation_errors,
            leave={
                'employee_id': employee_id,
                'leave_type': leave_type,
                'start_date': start_date,
                'end_date': end_date,
                'reason': reason,
                'status': status,
                'id': id
            }
        )

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leaves
        SET employee_id = %s,
            leave_type = %s,
            start_date = %s,
            end_date = %s,
            reason = %s,
            status = %s
        WHERE id = %s
    """, (employee_id, leave_type, start_date, end_date, reason, status, id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Leave updated successfully.')
    return redirect(url_for('leaves'))


@app.route("/leaves/<int:id>/delete", methods=["POST"])
@login_required
def leaves_delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM leaves WHERE id = %s", (id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM leaves WHERE id = %s", (id,))
        conn.commit()
        flash('Leave deleted successfully.')

    cursor.close()
    conn.close()

    return redirect(url_for('leaves'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


@app.route("/db-test")
def db_test():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        if result:
            return jsonify({"status": "success", "message": "Database connection works!"})
        return jsonify({"status": "error", "message": "Query returned no results"}), 500
    except Exception as e:
        print(f"Database connection error: {e}")
        return jsonify({"status": "error", "message": "Database connection failed"}), 500


if __name__ == "__main__":
    app.run(debug=DEBUG)
