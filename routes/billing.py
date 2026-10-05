"""Billing & payments routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from database.db import query
from routes.auth import login_required, get_current_user

billing_bp = Blueprint("billing", __name__)


@billing_bp.route("/bills")
@login_required
def bills_page():
    user = get_current_user()

    # Retrieve all patients for the dropdown selector
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

    # 3. Default to logged in user if patient
    if not target_patient:
        target_patient = query(
            """SELECT p.*, u.full_name, u.email, u.phone, u.username
               FROM patients p
               JOIN users u ON p.user_id = u.user_id
               WHERE p.user_id = ?""",
            (user["user_id"],),
            fetchone=True,
        )

    # 4. Fallback to first patient
    if not target_patient and all_patients:
        target_patient = all_patients[0]

    bills = []
    payments = []
    total_unpaid = 0.0
    total_billed = 0.0
    total_paid = 0.0
    breakdown = {"consultation": 0.0, "lab": 0.0, "pharmacy": 0.0, "other": 0.0}

    if target_patient:
        pid = target_patient["patient_id"]
        bills = query(
            "SELECT * FROM bills WHERE patient_id = ? ORDER BY date_issued DESC",
            (pid,),
        ) or []

        total_unpaid = sum(b["amount"] for b in bills if b["status"] == "unpaid")

        for b in bills:
            cat = b["category"] if b["category"] in breakdown else "other"
            breakdown[cat] += b["amount"]
        total_billed = sum(breakdown.values())

        payments = query(
            """SELECT p.*, b.description as bill_description FROM payments p
               JOIN bills b ON p.bill_id = b.bill_id
               WHERE p.patient_id = ? ORDER BY p.paid_at DESC""",
            (pid,),
        ) or []

        total_paid = sum(p["amount_paid"] for p in payments)

    return render_template(
        "bills.html",
        user=user,
        patient=target_patient,
        all_patients=all_patients,
        selected_patient_id=target_patient["patient_id"] if target_patient else None,
        search_query=search_query,
        bills=bills,
        total_unpaid=total_unpaid,
        breakdown=breakdown,
        total_billed=total_billed,
        total_paid=total_paid,
        payments=payments,
    )


@billing_bp.route("/bills/<int:bill_id>/pay", methods=["POST"])
@login_required
def pay_bill(bill_id):
    user = get_current_user()
    patient_id_param = request.form.get("patient_id")
    payment_method = request.form.get("payment_method", "Card").strip() or "Card"

    bill = query("SELECT * FROM bills WHERE bill_id = ?", (bill_id,), fetchone=True)
    if not bill:
        flash("Bill not found.", "danger")
    else:
        query("UPDATE bills SET status = 'paid' WHERE bill_id = ?", (bill_id,), commit=True)
        query(
            "INSERT INTO payments (bill_id, patient_id, amount_paid, payment_method) VALUES (?,?,?,?)",
            (bill_id, bill["patient_id"], bill["amount"], payment_method),
            commit=True,
        )
        report_url = url_for("patient.generate_report", patient_id=bill["patient_id"])
        flash(
            f"Payment of ₹{bill['amount']:.2f} via {payment_method} was successful! Bill #{bill_id} cleared. "
            f'<a href="{report_url}" target="_blank" class="btn btn-sm btn-primary" style="margin-left: 10px; text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">📄 View Updated Patient Status Report</a>',
            "success",
        )

    target_pid = patient_id_param or (bill["patient_id"] if bill else None)
    if target_pid:
        return redirect(url_for("billing.bills_page", patient_id=target_pid))
    return redirect(url_for("billing.bills_page"))


@billing_bp.route("/billing/invoice/<int:bill_id>")
@login_required
def view_invoice(bill_id):
    user = get_current_user()
    bill = query("SELECT * FROM bills WHERE bill_id = ?", (bill_id,), fetchone=True)
    if not bill:
        flash("Bill invoice not found.", "danger")
        return redirect(url_for("billing.bills_page"))

    patient = query(
        """SELECT p.*, u.full_name, u.email, u.phone, u.username
           FROM patients p
           JOIN users u ON p.user_id = u.user_id
           WHERE p.patient_id = ?""",
        (bill["patient_id"],),
        fetchone=True,
    )

    payments = query("SELECT * FROM payments WHERE bill_id = ? ORDER BY paid_at DESC", (bill_id,)) or []

    return render_template(
        "bill_invoice.html",
        user=user,
        bill=bill,
        patient=patient,
        payments=payments,
    )

