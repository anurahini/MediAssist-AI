"""
Triage Agent
------------
Reads the symptoms a user describes and suggests which hospital
department / type of doctor they should consult. This agent NEVER
diagnoses a condition or recommends medicine/dosage — it only maps
described symptoms to the appropriate department, always framed as a
suggestion, and always recommends seeing a qualified doctor for an
actual diagnosis. If wording suggests an emergency, the Orchestrator
routes to the Emergency Agent instead of this one.
"""
from database.db import query

_SYMPTOM_DEPT_MAP = {
    "fever": "General Medicine", "cough": "General Medicine", "cold": "General Medicine",
    "body ache": "General Medicine", "fatigue": "General Medicine", "weakness": "General Medicine",
    "headache": "Neurology", "migraine": "Neurology", "dizziness": "Neurology", "seizure": "Neurology",
    "chest pain": "Cardiology", "chest discomfort": "Cardiology", "palpitations": "Cardiology",
    "high blood pressure": "Cardiology",
    "back pain": "Orthopedics", "knee pain": "Orthopedics", "joint pain": "Orthopedics",
    "fracture": "Orthopedics", "sprain": "Orthopedics", "swelling": "Orthopedics",
    "stomach pain": "General Medicine", "abdominal pain": "General Medicine", "nausea": "General Medicine",
    "vomiting": "General Medicine", "diarrhea": "General Medicine",
    "rash": "Dermatology", "itching": "Dermatology", "allergy": "Dermatology", "burn": "Dermatology",
    "breathlessness": "Cardiology", "shortness of breath": "Cardiology",
    "sore throat": "ENT", "ear pain": "ENT", "toothache": "ENT",
    "eye pain": "Ophthalmology", "blurred vision": "Ophthalmology",
    "diabetes": "General Medicine",
    "burning urination": "Urology",
    "anxiety": "Psychiatry", "depression": "Psychiatry", "insomnia": "Psychiatry",
}


def _map_symptoms_to_departments(symptoms):
    depts = []
    for s in symptoms:
        d = _SYMPTOM_DEPT_MAP.get(s)
        if d and d not in depts:
            depts.append(d)
    return depts


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None) -> dict:
    symptoms = entities.get("symptoms", [])
    dept_names = _map_symptoms_to_departments(symptoms)

    disclaimer = ("\n\n⚠️ Please note: I'm not able to diagnose conditions or prescribe "
                  "treatment. This is only a suggestion for which specialist to see — a "
                  "qualified doctor will need to properly examine and diagnose you.")

    if not symptoms:
        msg = ("Could you describe your symptoms a bit more (e.g. \"headache and fever\", "
               "\"knee pain\", \"skin rash\")? I can then suggest which department to visit."
               + disclaimer)
        return {"text": msg, "data": {}}

    if not dept_names:
        msg = ("Based on what you've described, I'd recommend starting with our **General "
               "Medicine** department — they can assess you and refer you to a specialist "
               "if needed." + disclaimer)
        depts = query("SELECT * FROM departments WHERE name = 'General Medicine'", fetchone=True)
        return {"text": msg, "data": {"departments": [depts]}}

    depts = []
    for name in dept_names:
        d = query("SELECT * FROM departments WHERE name = ?", (name,), fetchone=True)
        if d:
            depts.append(d)

    dept_list_str = " or ".join(f"**{d['name']}**" for d in depts)
    doctors_lines = []
    for d in depts[:2]:
        docs = query("SELECT full_name, specialization FROM doctors WHERE department_id = ? "
                     "ORDER BY rating DESC LIMIT 2", (d["department_id"],))
        for doc in docs:
            doctors_lines.append(f"- {doc['full_name']} ({doc['specialization']}, {d['name']})")

    msg = (f"Based on the symptoms you described ({', '.join(symptoms)}), I'd suggest visiting "
           f"{dept_list_str}.")
    if doctors_lines:
        msg += "\n\nSome doctors you could see:\n" + "\n".join(doctors_lines)
    msg += "\n\nWould you like me to book an appointment for you?"
    msg += disclaimer

    return {"text": msg, "data": {"departments": depts, "symptoms": symptoms}}
