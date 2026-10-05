"""
Patient Agent
-------------
Gives a logged-in patient a personalized view of their own
appointments, lab reports, prescriptions, and combined medical
history. All queries are scoped strictly to the authenticated
patient's own patient_id to protect patient data.
"""
from database.db import query


def _get_patient_id(user):
    if not user:
        return None
    row = query("SELECT patient_id FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    return row["patient_id"] if row else None


def _medical_history_summary(patient_id):
    """Builds a combined, chronological text summary of past
    appointments (doctor consultations + symptoms), prescriptions, and
    lab reports - the same data shown on the Medical History page."""
    appointments = query(
        """SELECT a.*, d.full_name as doctor_name, dept.name as department_name
           FROM appointments a
           JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           WHERE a.patient_id = ? ORDER BY a.appointment_date DESC LIMIT 5""",
        (patient_id,),
    )
    prescriptions = query(
        """SELECT p.*, d.full_name as doctor_name FROM prescriptions p
           JOIN doctors d ON p.doctor_id = d.doctor_id
           WHERE p.patient_id = ? ORDER BY p.date_issued DESC LIMIT 5""",
        (patient_id,),
    )
    lab_reports = query(
        """SELECT r.*, t.test_name FROM lab_reports r
           JOIN lab_tests t ON r.test_id = t.test_id
           WHERE r.patient_id = ? ORDER BY r.booked_date DESC LIMIT 5""",
        (patient_id,),
    )

    if not appointments and not prescriptions and not lab_reports:
        return None

    parts = []
    if appointments:
        lines = [f"- {a['appointment_date']}: **{a['doctor_name']}** ({a['department_name']}) — "
                 f"{a['reason'] or 'Routine visit'} [{a['status']}]" for a in appointments]
        parts.append("**Past Consultations:**\n" + "\n".join(lines))
    if prescriptions:
        lines = [f"- {p['date_issued']}: by **{p['doctor_name']}** — {p['medicines']}" for p in prescriptions]
        parts.append("**Prescriptions:**\n" + "\n".join(lines))
    if lab_reports:
        lines = [f"- {r['booked_date']}: **{r['test_name']}** — {r['status']}" for r in lab_reports]
        parts.append("**Lab Reports:**\n" + "\n".join(lines))

    return "\n\n".join(parts), {"appointments": appointments, "prescriptions": prescriptions, "reports": lab_reports}


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None) -> dict:
    if not user:
        return {"text": "Please log in to your patient account so I can pull up your personal "
                         "records securely.", "data": {}, "requires_login": True}

    patient_id = _get_patient_id(user)
    lower = text.lower()

    report_gen_phrases = (
        "generate report", "download report", "get report", "print report",
        "full report", "patient report", "health report", "medical report",
        "my report", "summary report",
    )
    if any(p in lower for p in report_gen_phrases):
        report_url = f"/patient/{patient_id}/report"
        msg = (
            f"📄 **Patient Report Generated Successfully!**\n\n"
            f"Your comprehensive medical history, consultation records, prescriptions, lab results, "
            f"and billing summary have been compiled into an official hospital report.\n\n"
            f"👉 [**Click here to View & Print your Full Patient Report**]({report_url})\n\n"
            f"You can also save it as a PDF or present it during your next doctor consultation."
        )
        return {"text": msg, "data": {"report_url": report_url, "patient_id": patient_id}}

    history_phrases = (
        "medical history", "health record", "health history", "past visits",
        "previous visits", "past consultations", "treatment history",
        "past diagnoses", "case history", "patient history", "full history",
        "everything about my treatment", "my past records",
    )
    if any(p in lower for p in history_phrases):
        result = _medical_history_summary(patient_id)
        report_url = f"/patient/{patient_id}/report"
        if not result:
            return {"text": f"You don't have any medical history on record yet. You can still view your blank profile report here: [View Patient Report]({report_url})", "data": {}}
        summary_text, data = result
        msg = ("Here's a summary of your medical history:\n\n" + summary_text +
               f"\n\n📄 **Official Report**: [Click here to View & Print your Full Patient Report]({report_url})")
        return {"text": msg, "data": data}

    if "prescription" in lower or "medicine prescribed" in lower:
        rows = query(
            """SELECT p.*, d.full_name as doctor_name FROM prescriptions p
               JOIN doctors d ON p.doctor_id = d.doctor_id
               WHERE p.patient_id = ? ORDER BY p.date_issued DESC""",
            (patient_id,),
        )
        if not rows:
            return {"text": "You don't have any prescriptions on record yet.", "data": {}}
        lines = [f"- {r['date_issued']} by **{r['doctor_name']}**: {r['medicines']}" +
                 (f" — Note: {r['notes']}" if r['notes'] else "") for r in rows]
        return {"text": "Here are your prescriptions:\n\n" + "\n".join(lines), "data": {"prescriptions": rows}}

    if "report" in lower:
        rows = query(
            """SELECT r.*, t.test_name FROM lab_reports r
               JOIN lab_tests t ON r.test_id = t.test_id
               WHERE r.patient_id = ? ORDER BY r.booked_date DESC""",
            (patient_id,),
        )
        if not rows:
            return {"text": "You don't have any lab reports on record yet.", "data": {}}
        lines = [f"- **{r['test_name']}** ({r['booked_date']}): {r['status']}" for r in rows]
        return {"text": "Here are your lab reports:\n\n" + "\n".join(lines), "data": {"reports": rows}}

    # default -> appointments
    rows = query(
        """SELECT a.*, d.full_name as doctor_name, dept.name as department_name
           FROM appointments a
           JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           WHERE a.patient_id = ? ORDER BY a.appointment_date DESC""",
        (patient_id,),
    )
    if not rows:
        return {"text": "You don't have any appointments on record yet.", "data": {}}
    lines = [f"- **{r['doctor_name']}** ({r['department_name']}) on {r['appointment_date']} — {r['status']}"
             for r in rows]
    return {"text": "Here's your appointment history:\n\n" + "\n".join(lines), "data": {"appointments": rows}}
