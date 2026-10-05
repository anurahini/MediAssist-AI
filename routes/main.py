"""Main routes: landing page, dashboard, and dedicated emergency path."""
from flask import Blueprint, render_template, session, redirect, url_for

from database.db import query
from routes.auth import login_required, get_current_user
from agents.emergency_agent import EMERGENCY_HELPLINE, EMERGENCY_LOCATION

main_bp = Blueprint("main", __name__)


@main_bp.route("/emergency")
def emergency_page():
    """Dedicated, clearly visible emergency page using the existing emergency agent constants."""
    return render_template(
        "emergency.html",
        helpline=EMERGENCY_HELPLINE,
        location=EMERGENCY_LOCATION,
    )


@main_bp.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    patient = query("SELECT * FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)

    stats = {}
    if patient:
        stats["appointments"] = query(
            "SELECT COUNT(*) as c FROM appointments WHERE patient_id = ? AND status IN ('confirmed','rescheduled')",
            (patient["patient_id"],), fetchone=True)["c"]
        stats["reports_pending"] = query(
            "SELECT COUNT(*) as c FROM lab_reports WHERE patient_id = ? AND status != 'ready'",
            (patient["patient_id"],), fetchone=True)["c"]
        stats["unpaid_bills"] = query(
            "SELECT COUNT(*) as c FROM bills WHERE patient_id = ? AND status = 'unpaid'",
            (patient["patient_id"],), fetchone=True)["c"]
        stats["prescriptions"] = query(
            "SELECT COUNT(*) as c FROM prescriptions WHERE patient_id = ?",
            (patient["patient_id"],), fetchone=True)["c"]

        upcoming = query(
            """SELECT a.*, d.full_name as doctor_name, dept.name as department_name
               FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id
               JOIN departments dept ON d.department_id = dept.department_id
               WHERE a.patient_id = ? AND a.status IN ('confirmed','rescheduled')
               ORDER BY a.appointment_date ASC LIMIT 5""",
            (patient["patient_id"],))
    else:
        upcoming = []

    return render_template("dashboard.html", user=user, stats=stats, upcoming=upcoming)
