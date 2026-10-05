"""Pharmacy catalog routes."""
from flask import Blueprint, render_template, request

from database.db import query
from routes.auth import login_required

pharmacy_bp = Blueprint("pharmacy", __name__)


@pharmacy_bp.route("/pharmacy")
@login_required
def pharmacy_page():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "")

    sql = "SELECT * FROM medicines WHERE 1=1"
    params = []
    if search:
        sql += " AND name LIKE ?"
        params.append(f"%{search}%")
    if category:
        sql += " AND category = ?"
        params.append(category)
    sql += " ORDER BY category, name"

    medicines = query(sql, tuple(params))
    categories = query("SELECT DISTINCT category FROM medicines ORDER BY category")
    return render_template("pharmacy.html", medicines=medicines, categories=categories,
                          search=search, selected_category=category)


@pharmacy_bp.route("/prescriptions")
@login_required
def prescriptions_page():
    from routes.auth import get_current_user
    user = get_current_user()
    patient = query("SELECT * FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    rx = query(
        """SELECT p.*, d.full_name as doctor_name, d.specialization FROM prescriptions p
           JOIN doctors d ON p.doctor_id = d.doctor_id
           WHERE p.patient_id = ? ORDER BY p.date_issued DESC""",
        (patient["patient_id"],))
    return render_template("prescriptions.html", prescriptions=rx)
