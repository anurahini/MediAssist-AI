"""
Department Agent
-----------------
Answers questions about hospital departments: services offered,
timings and location.
"""
from database.db import query


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None,
           resolved_department=None) -> dict:
    lower = text.lower()

    if resolved_department:
        dept = query("SELECT * FROM departments WHERE department_id = ?",
                     (resolved_department["department_id"],), fetchone=True)
        if dept:
            msg = (f"**{dept['name']}** — {dept['description']}\n\n"
                   f"📍 Location: {dept['location']}\n"
                   f"🕐 Timings: {dept['timings']}\n"
                   f"🛠 Services: {dept['services']}\n"
                   f"☎ Extension: {dept['contact_ext']}")
            return {"text": msg, "data": {"department": dept}}

    if "list" in lower or "all department" in lower or "which department" in lower:
        depts = query("SELECT name, location FROM departments ORDER BY name")
        lines = "\n".join(f"- {d['name']} ({d['location']})" for d in depts)
        return {"text": f"Here are all our departments:\n\n{lines}", "data": {"departments": depts}}

    depts = query("SELECT name FROM departments ORDER BY name")
    dept_names = ", ".join(d["name"] for d in depts)
    return {"text": f"Which department would you like to know about? We have: {dept_names}.",
            "data": {"departments": depts}}
