"""Lab tests & reports routes."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash

from database.db import query
from routes.auth import login_required, get_current_user

lab_bp = Blueprint("lab", __name__)


@lab_bp.route("/lab-reports")
@login_required
def lab_reports():
    user = get_current_user()
    patient = query("SELECT * FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    reports = query(
        """SELECT r.*, t.test_name, t.category, t.price FROM lab_reports r
           JOIN lab_tests t ON r.test_id = t.test_id
           WHERE r.patient_id = ? ORDER BY r.booked_date DESC""",
        (patient["patient_id"],))
    tests = query("SELECT * FROM lab_tests ORDER BY category, test_name")
    return render_template("lab_reports.html", reports=reports, tests=tests, today=date.today().isoformat())


@lab_bp.route("/lab-reports/book", methods=["POST"])
@login_required
def book_test():
    user = get_current_user()
    patient = query("SELECT * FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    test_id = request.form.get("test_id")
    booked_date = request.form.get("booked_date")

    if not test_id or not booked_date:
        flash("Please choose a test and a date.", "danger")
        return redirect(url_for("lab.lab_reports"))

    query(
        "INSERT INTO lab_reports (patient_id, test_id, booked_date, status) VALUES (?,?,?,?)",
        (patient["patient_id"], test_id, booked_date, "pending"),
        commit=True,
    )
    flash("Lab test booked successfully.", "success")
    return redirect(url_for("lab.lab_reports"))
