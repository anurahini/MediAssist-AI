"""Patient profile routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from database.db import query
from routes.auth import login_required, get_current_user

patient_bp = Blueprint("patient", __name__)


@patient_bp.route("/profile")
@login_required
def profile():
    user = get_current_user()
    patient = query("SELECT * FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    return render_template("patient_profile.html", user=user, patient=patient)


@patient_bp.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    user = get_current_user()
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()
    emergency_contact = request.form.get("emergency_contact", "").strip()
    blood_group = request.form.get("blood_group", "").strip()

    query("UPDATE users SET full_name = ?, phone = ? WHERE user_id = ?",
          (full_name, phone, user["user_id"]), commit=True)
    query("UPDATE patients SET address = ?, emergency_contact = ?, blood_group = ? WHERE user_id = ?",
          (address, emergency_contact, blood_group, user["user_id"]), commit=True)

    flash("Profile updated successfully.", "success")
    return redirect(url_for("patient.profile"))


@patient_bp.route("/medical-history")
@login_required
def medical_history():
    """
    Patient Medical History page: supports patient selection/search by Name or ID,
    showing ONLY the selected patient's past visits, complaints/diagnosis records,
    prescriptions, lab reports, and treatment history.
    """
    user = get_current_user()

    # Retrieve all patients for the patient search/selector dropdown
    all_patients = query(
        """SELECT p.*, u.full_name, u.email, u.phone, u.username
           FROM patients p
           JOIN users u ON p.user_id = u.user_id
           ORDER BY u.full_name ASC"""
    ) or []

    search_query = request.args.get("q", "").strip()
    selected_pid_raw = request.args.get("patient_id", "").strip()

    target_patient = None

    # 1. Search by patient_id if explicitly provided
    if selected_pid_raw.isdigit():
        pid_int = int(selected_pid_raw)
        target_patient = query(
            """SELECT p.*, u.full_name, u.email, u.phone, u.username
               FROM patients p
               JOIN users u ON p.user_id = u.user_id
               WHERE p.patient_id = ?""",
            (pid_int,),
            fetchone=True,
        )

    # 2. Search by name/ID query if provided
    if not target_patient and search_query:
        if search_query.isdigit():
            target_patient = query(
                """SELECT p.*, u.full_name, u.email, u.phone, u.username
                   FROM patients p
                   JOIN users u ON p.user_id = u.user_id
                   WHERE p.patient_id = ?""",
                (int(search_query),),
                fetchone=True,
            )
        if not target_patient:
            target_patient = query(
                """SELECT p.*, u.full_name, u.email, u.phone, u.username
                   FROM patients p
                   JOIN users u ON p.user_id = u.user_id
                   WHERE u.full_name LIKE ? OR u.email LIKE ? OR u.phone LIKE ?
                   LIMIT 1""",
                (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"),
                fetchone=True,
            )

    # 3. Default to current logged in user (if patient)
    if not target_patient:
        target_patient = query(
            """SELECT p.*, u.full_name, u.email, u.phone, u.username
               FROM patients p
               JOIN users u ON p.user_id = u.user_id
               WHERE p.user_id = ?""",
            (user["user_id"],),
            fetchone=True,
        )

    # 4. Fallback to first patient in database
    if not target_patient and all_patients:
        target_patient = all_patients[0]

    timeline = []
    appointments = []
    prescriptions = []
    lab_reports = []

    if target_patient:
        pid = target_patient["patient_id"]

        appointments = query(
            """SELECT a.*, d.full_name as doctor_name, d.specialization, dept.name as department_name
               FROM appointments a
               JOIN doctors d ON a.doctor_id = d.doctor_id
               JOIN departments dept ON d.department_id = dept.department_id
               WHERE a.patient_id = ?
               ORDER BY a.appointment_date DESC, a.appointment_time DESC""",
            (pid,),
        ) or []

        for a in appointments:
            timeline.append({
                "type": "appointment",
                "date": a["appointment_date"],
                "time": a["appointment_time"],
                "icon": "🩺",
                "title": f"Consultation with {a['doctor_name']} ({a['department_name']})",
                "detail": f"Complaint / Diagnosis: {a['reason']}" if a["reason"] else "Routine consultation",
                "doctor": a["doctor_name"],
                "department": a["department_name"],
                "status": a["status"],
            })

        prescriptions = query(
            """SELECT p.*, d.full_name as doctor_name, dept.name as department_name
               FROM prescriptions p
               JOIN doctors d ON p.doctor_id = d.doctor_id
               JOIN departments dept ON d.department_id = dept.department_id
               WHERE p.patient_id = ?
               ORDER BY p.date_issued DESC""",
            (pid,),
        ) or []

        for p in prescriptions:
            timeline.append({
                "type": "prescription",
                "date": p["date_issued"],
                "icon": "📋",
                "title": f"Prescription by {p['doctor_name']}",
                "detail": f"Medicines: {p['medicines']}" + (f" | Notes/Instructions: {p['notes']}" if p["notes"] else ""),
                "medicines": p["medicines"],
                "notes": p["notes"],
                "doctor": p["doctor_name"],
                "status": None,
            })

        lab_reports = query(
            """SELECT r.*, t.test_name, t.category as test_category
               FROM lab_reports r
               JOIN lab_tests t ON r.test_id = t.test_id
               WHERE r.patient_id = ?
               ORDER BY r.booked_date DESC""",
            (pid,),
        ) or []

        for r in lab_reports:
            timeline.append({
                "type": "lab_report",
                "date": r["booked_date"],
                "icon": "🧪",
                "title": f"Lab Test: {r['test_name']} ({r['test_category']})",
                "detail": f"Summary: {r['result_summary']}" if r["result_summary"] else f"Report status: {r['status']}",
                "test_name": r["test_name"],
                "result_summary": r["result_summary"],
                "status": r["status"],
            })

        timeline.sort(key=lambda x: x["date"] or "", reverse=True)

    return render_template(
        "medical_history.html",
        user=user,
        patient=target_patient,
        all_patients=all_patients,
        selected_patient_id=target_patient["patient_id"] if target_patient else None,
        search_query=search_query,
        timeline=timeline,
        appointments=appointments,
        prescriptions=prescriptions,
        lab_reports=lab_reports,
    )


@patient_bp.route("/patient/report")
@patient_bp.route("/patient/<int:patient_id>/report")
@login_required
def generate_report(patient_id=None):
    from datetime import datetime
    user = get_current_user()

    target_patient = None
    if patient_id:
        target_patient = query(
            """SELECT p.*, u.full_name, u.email, u.phone, u.username
               FROM patients p
               JOIN users u ON p.user_id = u.user_id
               WHERE p.patient_id = ?""",
            (patient_id,),
            fetchone=True,
        )

    if not target_patient:
        # Default to logged in user if patient
        target_patient = query(
            """SELECT p.*, u.full_name, u.email, u.phone, u.username
               FROM patients p
               JOIN users u ON p.user_id = u.user_id
               WHERE p.user_id = ?""",
            (user["user_id"],),
            fetchone=True,
        )

    if not target_patient:
        first = query("SELECT patient_id FROM patients ORDER BY patient_id ASC LIMIT 1", fetchone=True)
        if first:
            target_patient = query(
                """SELECT p.*, u.full_name, u.email, u.phone, u.username
                   FROM patients p
                   JOIN users u ON p.user_id = u.user_id
                   WHERE p.patient_id = ?""",
                (first["patient_id"],),
                fetchone=True,
            )

    if not target_patient:
        flash("Patient not found.", "danger")
        return redirect(url_for("patient.medical_history"))

    pid = target_patient["patient_id"]

    appointments = query(
        """SELECT a.*, d.full_name as doctor_name, d.specialization, dept.name as department_name
           FROM appointments a
           JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           WHERE a.patient_id = ?
           ORDER BY a.appointment_date DESC, a.appointment_time DESC""",
        (pid,),
    ) or []

    prescriptions = query(
        """SELECT p.*, d.full_name as doctor_name
           FROM prescriptions p
           JOIN doctors d ON p.doctor_id = d.doctor_id
           WHERE p.patient_id = ?
           ORDER BY p.date_issued DESC""",
        (pid,),
    ) or []

    lab_reports = query(
        """SELECT r.*, t.test_name, t.category as test_category
           FROM lab_reports r
           JOIN lab_tests t ON r.test_id = t.test_id
           WHERE r.patient_id = ?
           ORDER BY r.booked_date DESC""",
        (pid,),
    ) or []

    bills = query("SELECT * FROM bills WHERE patient_id = ? ORDER BY date_issued DESC", (pid,)) or []
    payments = query(
        """SELECT p.*, b.description as bill_description FROM payments p
           JOIN bills b ON p.bill_id = b.bill_id
           WHERE p.patient_id = ? ORDER BY p.paid_at DESC""",
        (pid,),
    ) or []

    total_billed = sum(b["amount"] for b in bills)
    total_paid = sum(p["amount_paid"] for p in payments)
    total_unpaid = sum(b["amount"] for b in bills if b["status"] == "unpaid")

    now = datetime.now()
    generated_at = now.strftime("%Y-%m-%d %H:%M:%S")
    now_year = now.year

    return render_template(
        "patient_report.html",
        user=user,
        patient=target_patient,
        appointments=appointments,
        prescriptions=prescriptions,
        lab_reports=lab_reports,
        bills=bills,
        payments=payments,
        total_billed=total_billed,
        total_paid=total_paid,
        total_unpaid=total_unpaid,
        generated_at=generated_at,
        now_year=now_year,
    )

