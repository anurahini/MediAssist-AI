"""
Appointment Agent
------------------
Handles booking, cancelling, rescheduling and checking appointments.
Supports multi-turn slot filling via the conversation context, e.g.:

    User: "Book Dr. Arun."
    Bot:  "Sure — what date works for you?"
    User: "Tomorrow."
    Bot:  "Booked! ..."

All booking/cancel/reschedule actions require a logged-in patient.
"""
from datetime import datetime, timedelta
from database.db import query
from nlp import context_manager as ctx_mgr

_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _get_patient_id(user):
    if not user:
        return None
    row = query("SELECT patient_id FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    return row["patient_id"] if row else None


def _find_doctor_by_id(doctor_id):
    return query("SELECT * FROM doctors WHERE doctor_id = ?", (doctor_id,), fetchone=True)


def _doctor_works_on(doctor, appt_date: str) -> bool:
    """Check the requested date's weekday against the doctor's available_days."""
    try:
        day = datetime.strptime(appt_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return True  # can't validate an unparsable date; don't block booking
    weekday_abbr = _WEEKDAY_NAMES[day.weekday()]
    available_days = [d.strip()[:3] for d in (doctor["available_days"] or "").split(",")]
    return weekday_abbr in available_days


def _slot_grid(doctor):
    """Generate 30-minute appointment slots across the doctor's available_time window."""
    try:
        start_str, end_str = doctor["available_time"].split("-")
        start = datetime.strptime(start_str.strip(), "%H:%M")
        end = datetime.strptime(end_str.strip(), "%H:%M")
    except (ValueError, AttributeError):
        return ["09:00"]
    slots = []
    cur = start
    while cur < end:
        slots.append(cur.strftime("%H:%M"))
        cur += timedelta(minutes=30)
    return slots or ["09:00"]


def _booked_times(doctor_id, appt_date):
    rows = query(
        "SELECT appointment_time FROM appointments WHERE doctor_id = ? AND appointment_date = ? "
        "AND status IN ('confirmed','rescheduled')",
        (doctor_id, appt_date),
    )
    return {r["appointment_time"] for r in rows}


def _next_available_slot(doctor, appt_date):
    """
    Returns the first open 30-min slot for this doctor on this date, or
    None if the doctor doesn't work that day or is fully booked.
    """
    if not _doctor_works_on(doctor, appt_date):
        return None
    taken = _booked_times(doctor["doctor_id"], appt_date)
    for slot in _slot_grid(doctor):
        if slot not in taken:
            return slot
    return "FULL"


def _full_doctors(doctor_list):
    """
    Entities/context only carry {doctor_id, full_name} for a matched
    doctor - re-hydrate to the full DB row (needed for available_time,
    specialization, etc.) before using it for booking.
    """
    if not doctor_list:
        return []
    full = []
    for d in doctor_list:
        row = _find_doctor_by_id(d["doctor_id"])
        if row:
            full.append(row)
    return full


def _upcoming_appointments(patient_id):
    return query(
        """SELECT a.*, d.full_name as doctor_name, dept.name as department_name
           FROM appointments a
           JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           WHERE a.patient_id = ? AND a.status IN ('confirmed','rescheduled')
           ORDER BY a.appointment_date ASC""",
        (patient_id,),
    )


def _all_appointments(patient_id):
    return query(
        """SELECT a.*, d.full_name as doctor_name, dept.name as department_name
           FROM appointments a
           JOIN doctors d ON a.doctor_id = d.doctor_id
           JOIN departments dept ON d.department_id = dept.department_id
           WHERE a.patient_id = ?
           ORDER BY a.appointment_date DESC""",
        (patient_id,),
    )


def _book(patient_id, doctor, appt_date, reason=""):
    """
    Books an appointment only after checking the doctor's weekly
    availability and finding a free slot on the requested date.
    Returns (appointment_id, time_slot, error) — error is None on
    success, or one of "not_working"/"fully_booked" on failure.
    """
    slot = _next_available_slot(doctor, appt_date)
    if slot is None:
        return None, None, "not_working"
    if slot == "FULL":
        return None, None, "fully_booked"

    new_id = query(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) "
        "VALUES (?,?,?,?,?,?)",
        (patient_id, doctor["doctor_id"], appt_date, slot, "confirmed", reason or "General consultation"),
        commit=True,
    )
    return new_id, slot, None


def _availability_error_message(doctor, appt_date, error):
    if error == "not_working":
        return (f"**{doctor['full_name']}** doesn't see patients on that day — available days are "
                f"**{doctor['available_days']}**. Could you pick a different date?")
    if error == "fully_booked":
        return (f"**{doctor['full_name']}** is fully booked on **{appt_date}**. Would you like to try "
                f"another date, or another doctor in the same department?")
    return "Sorry, I couldn't book that appointment. Could you try a different date?"


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None,
           resolved_doctors=None, resolved_department=None) -> dict:

    patient_id = _get_patient_id(user)
    lower = text.lower()
    dates = entities.get("dates", [])
    resolved_date = dates[0]["resolved_date"] if dates and dates[0]["resolved_date"] else None

    ctx = ctx_mgr.get_context(session_id)
    pending = ctx.pending_action
    pending_data = ctx.pending_data or {}

    resolved_doctors = _full_doctors(resolved_doctors)

    if not user:
        login_msg = ("You'll need to log in to your patient account before I can manage "
                      "appointments. Please log in or register, then come back and I'll "
                      "pick up right where we left off.")
        return {"text": login_msg, "data": {}, "requires_login": True}

    # ------------------------------------------------------------------
    # Continue a pending multi-turn booking (e.g. we already know the
    # doctor and are waiting only for the date).
    # ------------------------------------------------------------------
    if pending == "appointment_awaiting_date":
        if resolved_date:
            doctor = _find_doctor_by_id(pending_data["doctor_id"])
            appt_id, time_slot, error = _book(patient_id, doctor, resolved_date, pending_data.get("reason"))
            if error:
                return {"text": _availability_error_message(doctor, resolved_date, error), "data": {}}
            ctx_mgr.clear_pending_action(session_id)
            msg = (f"✅ Your appointment with **{doctor['full_name']}** ({doctor['specialization']}) "
                   f"is confirmed for **{resolved_date} at {time_slot}**. Appointment ID: {appt_id}.")
            return {"text": msg, "data": {"appointment_id": appt_id}}
        else:
            return {"text": "Sorry, I didn't catch a date. Could you tell me the date for your "
                             "appointment (e.g. \"tomorrow\" or \"next Monday\")?", "data": {}}

    if pending == "appointment_awaiting_doctor_for_date":
        doctors = resolved_doctors or _full_doctors(ctx_mgr.resolve_doctor_reference(session_id, entities))
        if doctors:
            doctor = doctors[0]
            appt_date = pending_data["date"]
            appt_id, time_slot, error = _book(patient_id, doctor, appt_date, pending_data.get("reason"))
            if error:
                return {"text": _availability_error_message(doctor, appt_date, error), "data": {}}
            ctx_mgr.clear_pending_action(session_id)
            msg = (f"✅ Your appointment with **{doctor['full_name']}** is confirmed for "
                   f"**{appt_date} at {time_slot}**. Appointment ID: {appt_id}.")
            return {"text": msg, "data": {"appointment_id": appt_id}}
        else:
            return {"text": "Which doctor would you like to book with?", "data": {}}

    if pending == "appointment_awaiting_cancel_choice":
        candidates = pending_data.get("appointments", [])
        chosen = None
        for a in candidates:
            if str(a["appointment_id"]) in lower or a["doctor_name"].split()[-1].lower() in lower:
                chosen = a
                break
        if not chosen and len(candidates) == 1:
            chosen = candidates[0]
        if chosen:
            query("UPDATE appointments SET status = 'cancelled' WHERE appointment_id = ?",
                  (chosen["appointment_id"],), commit=True)
            ctx_mgr.clear_pending_action(session_id)
            return {"text": f"Your appointment with {chosen['doctor_name']} on {chosen['appointment_date']} "
                             f"has been cancelled.", "data": {}}
        else:
            opts = "\n".join(f"- ID {a['appointment_id']}: {a['doctor_name']} on {a['appointment_date']}" for a in candidates)
            return {"text": f"Which appointment would you like to cancel?\n\n{opts}", "data": {}}

    if pending == "appointment_awaiting_reschedule_date":
        if resolved_date:
            appt_id = pending_data["appointment_id"]
            query("UPDATE appointments SET appointment_date = ?, status='rescheduled' WHERE appointment_id = ?",
                  (resolved_date, appt_id), commit=True)
            ctx_mgr.clear_pending_action(session_id)
            return {"text": f"Done! Your appointment (ID {appt_id}) has been rescheduled to **{resolved_date}**.",
                    "data": {}}
        else:
            return {"text": "What new date would you like for this appointment?", "data": {}}

    # ------------------------------------------------------------------
    # Fresh intents
    # ------------------------------------------------------------------
    if any(w in lower for w in ["cancel"]):
        upcoming = _upcoming_appointments(patient_id)
        if not upcoming:
            return {"text": "You don't have any upcoming appointments to cancel.", "data": {}}
        if len(upcoming) == 1:
            a = upcoming[0]
            query("UPDATE appointments SET status = 'cancelled' WHERE appointment_id = ?",
                  (a["appointment_id"],), commit=True)
            return {"text": f"Your appointment with {a['doctor_name']} on {a['appointment_date']} "
                             f"has been cancelled.", "data": {}}
        ctx_mgr.set_pending_action(session_id, "appointment_awaiting_cancel_choice", {"appointments": upcoming})
        opts = "\n".join(f"- ID {a['appointment_id']}: {a['doctor_name']} on {a['appointment_date']}" for a in upcoming)
        return {"text": f"You have a few upcoming appointments:\n\n{opts}\n\nWhich one would you like to cancel?",
                "data": {"appointments": upcoming}}

    if any(w in lower for w in ["reschedule", "postpone", "shift", "move my appointment", "change my appointment"]):
        upcoming = _upcoming_appointments(patient_id)
        if not upcoming:
            return {"text": "You don't have any upcoming appointments to reschedule.", "data": {}}
        target = upcoming[0]
        if resolved_date:
            query("UPDATE appointments SET appointment_date = ?, status='rescheduled' WHERE appointment_id = ?",
                  (resolved_date, target["appointment_id"]), commit=True)
            return {"text": f"Done! Your appointment with {target['doctor_name']} has been rescheduled to "
                             f"**{resolved_date}**.", "data": {}}
        ctx_mgr.set_pending_action(session_id, "appointment_awaiting_reschedule_date",
                                    {"appointment_id": target["appointment_id"]})
        return {"text": f"Your appointment with {target['doctor_name']} is currently on "
                         f"{target['appointment_date']}. What new date would you like?", "data": {}}

    if any(w in lower for w in ["show", "check", "my appointment", "upcoming", "do i have"]):
        appts = _all_appointments(patient_id)
        if not appts:
            return {"text": "You don't have any appointments on record yet. Would you like to book one?",
                    "data": {}}
        lines = [f"- **{a['doctor_name']}** ({a['department_name']}) on {a['appointment_date']} at "
                 f"{a['appointment_time']} — status: {a['status']}" for a in appts]
        return {"text": "Here are your appointments:\n\n" + "\n".join(lines), "data": {"appointments": appts}}

    # Default: treat as a booking request
    doctors = resolved_doctors or _full_doctors(ctx_mgr.resolve_doctor_reference(session_id, entities))
    if doctors and resolved_date:
        doctor = doctors[0]
        appt_id, time_slot, error = _book(patient_id, doctor, resolved_date)
        if error:
            return {"text": _availability_error_message(doctor, resolved_date, error), "data": {}}
        msg = (f"✅ Your appointment with **{doctor['full_name']}** ({doctor['specialization']}) is "
               f"confirmed for **{resolved_date} at {time_slot}**. Appointment ID: {appt_id}.")
        return {"text": msg, "data": {"appointment_id": appt_id}}

    if doctors and not resolved_date:
        ctx_mgr.set_pending_action(session_id, "appointment_awaiting_date", {"doctor_id": doctors[0]["doctor_id"]})
        return {"text": f"Sure — what date works for your appointment with **{doctors[0]['full_name']}**?",
                "data": {}}

    if resolved_date and not doctors:
        ctx_mgr.set_pending_action(session_id, "appointment_awaiting_doctor_for_date", {"date": resolved_date})
        return {"text": f"Got it, {resolved_date} works. Which doctor would you like to see?", "data": {}}

    return {"text": "I'd be happy to help you book an appointment. Which doctor or department would you "
                     "like, and what date works for you?", "data": {}}
