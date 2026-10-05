"""Appointment management routes (dashboard forms, not chatbot)."""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash

from database.db import query
from routes.auth import login_required, get_current_user

appointments_bp = Blueprint("appointments", __name__)


def _get_patient(user):
    return query("SELECT * FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)


@appointments_bp.route("/appointments")
@login_required
def list_appointments():
    user = get_current_user()
    patient = _get_patient(user)
    appts = query(
        """SELECT a.*, d.full_name as doctor_name, d.specialization, dept.name as department_name
           FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           WHERE a.patient_id = ? ORDER BY a.appointment_date DESC""",
        (patient["patient_id"],))
    doctor_list = query("SELECT doctor_id, full_name, specialization, available_days, available_time FROM doctors ORDER BY full_name")
    return render_template("appointments.html", appointments=appts, doctors=doctor_list, today=date.today().isoformat())


@appointments_bp.route("/appointments/book", methods=["POST"])
@login_required
def book_appointment():
    user = get_current_user()
    patient = _get_patient(user)
    doctor_id = request.form.get("doctor_id")
    appt_date = request.form.get("appointment_date")
    appt_time = request.form.get("appointment_time")
    reason = request.form.get("reason", "General consultation")

    if not doctor_id or not appt_date or not appt_time:
        flash("Please fill in doctor, date and time.", "danger")
        return redirect(url_for("appointments.list_appointments"))

    query(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) "
        "VALUES (?,?,?,?,?,?)",
        (patient["patient_id"], doctor_id, appt_date, appt_time, "confirmed", reason),
        commit=True,
    )
    flash("Appointment booked successfully!", "success")
    return redirect(url_for("appointments.list_appointments"))


@appointments_bp.route("/appointments/<int:appointment_id>/cancel", methods=["POST"])
@login_required
def cancel_appointment(appointment_id):
    user = get_current_user()
    patient = _get_patient(user)
    appt = query("SELECT * FROM appointments WHERE appointment_id = ? AND patient_id = ?",
                (appointment_id, patient["patient_id"]), fetchone=True)
    if not appt:
        flash("Appointment not found.", "danger")
    else:
        query("UPDATE appointments SET status = 'cancelled' WHERE appointment_id = ?",
              (appointment_id,), commit=True)
        flash("Appointment cancelled.", "info")
    return redirect(url_for("appointments.list_appointments"))


@appointments_bp.route("/appointments/<int:appointment_id>/reschedule", methods=["POST"])
@login_required
def reschedule_appointment(appointment_id):
    user = get_current_user()
    patient = _get_patient(user)
    new_date = request.form.get("new_date")
    new_time = request.form.get("new_time")
    appt = query("SELECT * FROM appointments WHERE appointment_id = ? AND patient_id = ?",
                (appointment_id, patient["patient_id"]), fetchone=True)
    if not appt or not new_date or not new_time:
        flash("Unable to reschedule appointment.", "danger")
    else:
        query("UPDATE appointments SET appointment_date = ?, appointment_time = ?, status = 'rescheduled' "
              "WHERE appointment_id = ?", (new_date, new_time, appointment_id), commit=True)
        flash("Appointment rescheduled successfully.", "success")
    return redirect(url_for("appointments.list_appointments"))
