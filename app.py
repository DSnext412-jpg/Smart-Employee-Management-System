from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from dotenv import load_dotenv
import os
import MySQLdb

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
    """Get a MySQL database connection using configuration."""
    return MySQLdb.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        passwd=app.config["MYSQL_PASSWORD"],
        db=app.config["MYSQL_DB"],
        port=app.config["MYSQL_PORT"],
    )


def login_required(f):
    """Decorator to protect routes requiring authentication."""
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
    """Login route - display login form and handle authentication."""
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

        if user and user[3] == password:
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[4]
            return redirect(url_for("dashboard"))
        else:
            return render_template(
                "login.html",
                error="Invalid username or password.",
            )

    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout route - clear session and redirect to login."""
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Protected dashboard page - requires login."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM employees")
    total_employees = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM departments")
    total_departments = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM attendance WHERE date = CURDATE()")
    today_attendance = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leaves WHERE status = 'pending'")
    pending_leaves = cursor.fetchone()[0]

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
    """Employee list page with search."""
    search_term = request.args.get('search', '')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

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
    """Show add employee form."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("employee_form.html", employee_form_title="Add Employee", departments=departments)


@app.route("/employees/add", methods=["POST"])
@login_required
def employees_add_post():
    """Process add employee form."""
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

    # Required field validation
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

    # Basic email validation
    if email and '@' not in email:
        validation_errors['email'] = 'Please enter a valid email address.'

    # Employee ID duplicate check
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
        cursor = conn.cursor(dictionary=True)
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

    return redirect(url_for('employees'))


@app.route("/employees/<int:id>")
@login_required
def employee_details(id):
    """View employee details."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
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
        return redirect(url_for('employees'))

    return render_template("employee_details.html", employee=employee)


@app.route("/employees/<int:id>/edit")
@login_required
def employee_edit(id):
    """Show edit employee form."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
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
        return redirect(url_for('employees'))

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
    """Process edit employee form."""
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

    validation_errors = {}

    if not employee_id:
        validation_errors['employee_id'] = 'Employee ID is required.'

    if email and '@' not in email:
        validation_errors['email'] = 'Please enter a valid email address.'

    hire_date = request.form.get('hire_date', '').strip()

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

    # Employee ID uniqueness check (exclude current employee)
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
        cursor = conn.cursor(dictionary=True)
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

    return redirect(url_for('employee_details', id=id))


@app.route("/employees/<int:id>/delete", methods=["POST"])
@login_required
def employee_delete(id):
    """Delete employee."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM employees WHERE id = %s", (id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("DELETE FROM employees WHERE id = %s", (id,))
        conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for('employees'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


@app.route("/db-test")
def db_test():
    """Simple test route to verify MySQL connection."""
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
