"""
Authentication routes: register, login, logout.
Uses Flask's server-side session (signed cookie) to track the logged
in user. Passwords are hashed with werkzeug's PBKDF2-based hasher -
never stored in plain text.
"""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import query

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def get_current_user():
    if "user_id" not in session:
        return None
    return query("SELECT * FROM users WHERE user_id = ?", (session["user_id"],), fetchone=True)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        dob = request.form.get("date_of_birth", "")
        gender = request.form.get("gender", "")
        blood_group = request.form.get("blood_group", "")

        if not all([full_name, username, email, password]):
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")

        existing = query("SELECT user_id FROM users WHERE username = ? OR email = ?",
                         (username, email), fetchone=True)
        if existing:
            flash("Username or email already registered. Please log in instead.", "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        user_id = query(
            "INSERT INTO users (username, email, password_hash, role, full_name, phone) VALUES (?,?,?,?,?,?)",
            (username, email, password_hash, "patient", full_name, phone),
            commit=True,
        )
        query(
            "INSERT INTO patients (user_id, date_of_birth, gender, blood_group, address, emergency_contact) "
            "VALUES (?,?,?,?,?,?)",
            (user_id, dob, gender, blood_group, "", ""),
            commit=True,
        )

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        user = query("SELECT * FROM users WHERE username = ? OR email = ?",
                     (identifier, identifier), fetchone=True)

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Invalid username/email or password.", "danger")
            return render_template("login.html")

        if not user["is_active"]:
            flash("This account has been deactivated. Please contact the hospital.", "danger")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["user_id"]
        session["username"] = user["username"]
        session["full_name"] = user["full_name"]
        session["role"] = user["role"]

        flash(f"Welcome back, {user['full_name']}!", "success")
        next_page = request.args.get("next")
        if user["role"] == "admin":
            return redirect(next_page or url_for("admin.dashboard"))
        return redirect(next_page or url_for("main.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
