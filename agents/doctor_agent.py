"""
Doctor Agent
------------
Answers questions about doctors: who's available in a department,
a specific doctor's specialization/availability/fee, etc.
"""
from database.db import query

_SYMPTOM_TO_DEPT = {
    "heart": "Cardiology", "cardiac": "Cardiology", "chest": "Cardiology",
    "skin": "Dermatology", "rash": "Dermatology", "acne": "Dermatology",
    "bone": "Orthopedics", "joint": "Orthopedics", "knee": "Orthopedics", "fracture": "Orthopedics",
    "child": "Pediatrics", "kid": "Pediatrics", "baby": "Pediatrics",
    "eye": "Ophthalmology", "vision": "Ophthalmology",
    "ear": "ENT", "nose": "ENT", "throat": "ENT", "sinus": "ENT",
    "brain": "Neurology", "headache": "Neurology", "migraine": "Neurology", "seizure": "Neurology",
    "kidney": "Urology", "urine": "Urology", "urinary": "Urology",
    "pregnan": "Gynecology", "women": "Gynecology", "gynec": "Gynecology",
    "mental": "Psychiatry", "anxiety": "Psychiatry", "depression": "Psychiatry", "stress": "Psychiatry",
    "fever": "General Medicine", "cold": "General Medicine", "diabetes": "General Medicine",
}


def _guess_department_from_text(text: str):
    lower = text.lower()
    for kw, dept in _SYMPTOM_TO_DEPT.items():
        if kw in lower:
            return dept
    return None


def _format_doctor_line(doc):
    return (f"**{doc['full_name']}** — {doc['specialization']} "
            f"({doc['experience_years']} yrs exp.), available {doc['available_days']} "
            f"at {doc['available_time']}, consultation fee ₹{int(doc['consultation_fee'])}")


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None,
           resolved_doctors=None, resolved_department=None) -> dict:

    # 1) A specific doctor was named -> give full details
    if resolved_doctors:
        lines = []
        for doc in resolved_doctors:
            full = query("SELECT d.*, dept.name as department_name FROM doctors d "
                         "JOIN departments dept ON d.department_id = dept.department_id "
                         "WHERE d.doctor_id = ?", (doc["doctor_id"],), fetchone=True)
            if full:
                lines.append(_format_doctor_line(full) + f", Dept: {full['department_name']}, Room {full['room_no']}")
        if lines:
            msg = "Here's what I found:\n\n" + "\n\n".join(lines)
            msg += "\n\nWould you like to book an appointment with one of them?"
            return {"text": msg, "data": {"doctors": resolved_doctors}}

    # 2) A department was mentioned or resolvable via context
    dept = resolved_department
    if not dept:
        dept_name = _guess_department_from_text(text)
        if dept_name:
            dept = query("SELECT * FROM departments WHERE name = ?", (dept_name,), fetchone=True)

    if dept:
        doctors = query(
            "SELECT * FROM doctors WHERE department_id = ? ORDER BY rating DESC",
            (dept["department_id"],),
        )
        if doctors:
            lines = [_format_doctor_line(d) for d in doctors]
            msg = (f"Sure, our **{dept['name']}** department has:\n\n" + "\n\n".join(lines) +
                   "\n\nWould you like me to book an appointment with any of them? "
                   "Just tell me the name and a date, e.g. \"Book Dr. Arun tomorrow\".")
            return {"text": msg, "data": {"department": dept, "doctors": doctors}}

    # 3) No department/doctor identified — ask a clarifying question, list all departments
    all_depts = query("SELECT name FROM departments ORDER BY name")
    dept_names = ", ".join(d["name"] for d in all_depts)
    msg = ("I can help you find the right doctor. Could you tell me the specialization or "
           "department you're looking for (e.g. Cardiology, Orthopedics), or describe your "
           f"symptom?\n\nOur departments: {dept_names}.")
    return {"text": msg, "data": {"departments": all_depts}}
