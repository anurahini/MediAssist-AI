"""Doctor directory routes."""
from flask import Blueprint, render_template, request

from database.db import query
from routes.auth import login_required

doctors_bp = Blueprint("doctors", __name__)


@doctors_bp.route("/doctors")
@login_required
def list_doctors():
    dept_filter = request.args.get("department", "")
    search = request.args.get("q", "").strip()

    sql = """SELECT d.*, dept.name as department_name FROM doctors d
              JOIN departments dept ON d.department_id = dept.department_id WHERE 1=1"""
    params = []
    if dept_filter:
        sql += " AND dept.name = ?"
        params.append(dept_filter)
    if search:
        sql += " AND (d.full_name LIKE ? OR d.specialization LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY dept.name, d.rating DESC"

    doctor_list = query(sql, tuple(params))
    departments = query("SELECT name FROM departments ORDER BY name")

    return render_template("doctors.html", doctors=doctor_list, departments=departments,
                          selected_dept=dept_filter, search=search)
