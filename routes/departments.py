"""Department directory routes."""
from flask import Blueprint, render_template

from database.db import query
from routes.auth import login_required

departments_bp = Blueprint("departments", __name__)


@departments_bp.route("/departments")
@login_required
def list_departments():
    dept_list = query("SELECT * FROM departments ORDER BY name")
    for d in dept_list:
        d["doctor_count"] = query(
            "SELECT COUNT(*) as c FROM doctors WHERE department_id = ?",
            (d["department_id"],), fetchone=True)["c"]
    return render_template("departments.html", departments=dept_list)
