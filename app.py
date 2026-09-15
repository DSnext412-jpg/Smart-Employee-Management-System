from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from dotenv import load_dotenv
import os
import MySQLdb
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT, SECRET_KEY, DEBUG

# Load environment variables from .env file
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
    # If already logged in, redirect to home
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Validate fields are not empty
        if not username or not password:
            return render_template(
                "login.html",
                error="Username and password are required.",
            )

        conn = get_db_connection()
        cursor = conn.cursor()

        # Search the users table using parameterized query
        cursor.execute(
            "SELECT id, username, email, password, role FROM users WHERE username = %s OR email = %s",
            (username, username),
        )
        user = cursor.fetchone()
        conn.close()

        # Verify credentials (plain text comparison)
        if user and user[3] == password:
            # Login successful - store only necessary info in session
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[4]
            return redirect(url_for("dashboard"))
        else:
            # Invalid credentials - don't reveal if username or password was wrong
            return render_template(
                "login.html",
                error="Invalid username or password.",
            )

    # GET request - display login form
    return render_template("login.html")


@app.route("/logout")
def logout():
    """Logout route - clear session and redirect to login."""
    # Clear all session data
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    """Protected dashboard page - requires login."""
    return f"Welcome to Employee360\nWelcome, {session['username']}"


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
        # Log the exception in the development terminal
        print(f"Database connection error: {e}")
        return jsonify({"status": "error", "message": "Database connection failed"}), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=DEBUG)