"""
Lab Agent
---------
Answers questions about lab tests (price, preparation, turnaround time)
and lets logged-in patients check their report status.
"""
from database.db import query


def _get_patient_id(user):
    if not user:
        return None
    row = query("SELECT patient_id FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    return row["patient_id"] if row else None


def _find_tests_in_text(text):
    lower = text.lower()
    all_tests = query("SELECT * FROM lab_tests")
    matched = [t for t in all_tests if t["test_name"].split("(")[0].strip().lower() in lower
               or any(w.lower() in lower for w in t["test_name"].replace("(", "").replace(")", "").split() if len(w) > 3)]
    return matched


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None) -> dict:
    lower = text.lower()
    patient_id = _get_patient_id(user)

    if any(w in lower for w in ["status", "ready", "result", "when will"]):
        if not user:
            return {"text": "Please log in to your patient account so I can check your lab report status.",
                    "data": {}, "requires_login": True}
        reports = query(
            """SELECT r.*, t.test_name FROM lab_reports r
               JOIN lab_tests t ON r.test_id = t.test_id
               WHERE r.patient_id = ? ORDER BY r.booked_date DESC""",
            (patient_id,),
        )
        if not reports:
            return {"text": "You don't have any lab tests on record.", "data": {}}
        lines = []
        for r in reports:
            status_line = f"- **{r['test_name']}** (booked {r['booked_date']}): status **{r['status']}**"
            if r["status"] == "ready" and r["result_summary"]:
                status_line += f" — {r['result_summary']}"
            lines.append(status_line)
        return {"text": "Here's your lab report status:\n\n" + "\n".join(lines), "data": {"reports": reports}}

    matched = _find_tests_in_text(text)
    if matched:
        lines = []
        for t in matched:
            lines.append(f"**{t['test_name']}** — ₹{int(t['price'])}, prep: {t['preparation']}, "
                         f"report in {t['report_time']}")
        return {"text": "Here's what I found:\n\n" + "\n\n".join(lines), "data": {"tests": matched}}

    if "list" in lower or "available test" in lower or "what test" in lower:
        tests = query("SELECT test_name, category, price FROM lab_tests ORDER BY category")
        lines = "\n".join(f"- {t['test_name']} ({t['category']}) — ₹{int(t['price'])}" for t in tests)
        return {"text": f"Here are our available lab tests:\n\n{lines}", "data": {"tests": tests}}

    return {"text": "I can help with lab test prices, preparation instructions, or your report "
                     "status. Which test are you asking about, or would you like to see the "
                     "full list of tests we offer?", "data": {}}
