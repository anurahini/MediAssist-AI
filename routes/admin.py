"""Admin dashboard routes - hospital-wide overview and management."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from database.db import query
from routes.auth import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_required
def dashboard():
    stats = {
        "total_patients": query("SELECT COUNT(*) as c FROM patients", fetchone=True)["c"],
        "total_doctors": query("SELECT COUNT(*) as c FROM doctors", fetchone=True)["c"],
        "total_appointments": query("SELECT COUNT(*) as c FROM appointments", fetchone=True)["c"],
        "today_appointments": query(
            "SELECT COUNT(*) as c FROM appointments WHERE appointment_date = date('now')", fetchone=True)["c"],
        "pending_bills": query("SELECT COUNT(*) as c FROM bills WHERE status='unpaid'", fetchone=True)["c"],
        "total_revenue": query("SELECT COALESCE(SUM(amount),0) as s FROM bills WHERE status='paid'", fetchone=True)["s"],
        "total_chats": query("SELECT COUNT(*) as c FROM chat_logs", fetchone=True)["c"],
        "emergency_alerts": query("SELECT COUNT(*) as c FROM chat_logs WHERE intent='emergency'", fetchone=True)["c"],
    }

    recent_appointments = query(
        """SELECT a.*, p_u.full_name as patient_name, d.full_name as doctor_name
           FROM appointments a
           JOIN patients p ON a.patient_id = p.patient_id
           JOIN users p_u ON p.user_id = p_u.user_id
           JOIN doctors d ON a.doctor_id = d.doctor_id
           ORDER BY a.created_at DESC LIMIT 10""")

    intent_breakdown = query(
        "SELECT agent, COUNT(*) as c FROM chat_logs GROUP BY agent ORDER BY c DESC")

    recent_chats = query(
        "SELECT * FROM chat_logs ORDER BY created_at DESC LIMIT 15")

    return render_template("admin.html", stats=stats, recent_appointments=recent_appointments,
                          intent_breakdown=intent_breakdown, recent_chats=recent_chats)


@admin_bp.route("/admin/patients")
@admin_required
def patients_list():
    patients = query(
        """SELECT p.*, u.full_name, u.email, u.phone FROM patients p
           JOIN users u ON p.user_id = u.user_id ORDER BY u.full_name""")
    return render_template("admin_patients.html", patients=patients)


@admin_bp.route("/admin/appointments")
@admin_required
def appointments_list():
    appts = query(
        """SELECT a.*, p_u.full_name as patient_name, d.full_name as doctor_name, dept.name as department_name
           FROM appointments a
           JOIN patients p ON a.patient_id = p.patient_id
           JOIN users p_u ON p.user_id = p_u.user_id
           JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           ORDER BY a.appointment_date DESC""")
    return render_template("admin_appointments.html", appointments=appts)


@admin_bp.route("/admin/appointments/<int:appointment_id>/status", methods=["POST"])
@admin_required
def update_appointment_status(appointment_id):
    new_status = request.form.get("status")
    if new_status in ("confirmed", "cancelled", "completed", "rescheduled"):
        query("UPDATE appointments SET status = ? WHERE appointment_id = ?",
              (new_status, appointment_id), commit=True)
        flash("Appointment status updated.", "success")
    return redirect(url_for("admin.appointments_list"))
