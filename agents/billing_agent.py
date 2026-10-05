"""
Billing Agent
-------------
Handles bill inquiries, payment status, patient-wise billing history
(with a consultation/lab/pharmacy charges breakdown and payment
transaction history), and general insurance questions for the
logged-in patient.
"""
from database.db import query


def _get_patient_id(user):
    if not user:
        return None
    row = query("SELECT patient_id FROM patients WHERE user_id = ?", (user["user_id"],), fetchone=True)
    return row["patient_id"] if row else None


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None) -> dict:
    lower = text.lower()

    if "insurance" in lower and "cover" not in lower and "bill" not in lower and "claim" not in lower:
        msg = ("We accept most major health insurance providers for cashless treatment, "
               "including Star Health, HDFC Ergo, ICICI Lombard, and National Insurance. "
               "Please carry your insurance card and ID for verification at the billing desk. "
               "Ask me about a specific bill if you'd like to check its insurance coverage.")
        return {"text": msg, "data": {}}

    if not user:
        return {"text": "Please log in to your patient account so I can pull up your billing "
                         "details securely.", "data": {}, "requires_login": True}

    patient_id = _get_patient_id(user)

    if "pay" in lower and "bill" in lower or "make a payment" in lower or "settle" in lower or "clear my due" in lower:
        unpaid = query("SELECT * FROM bills WHERE patient_id = ? AND status = 'unpaid'", (patient_id,))
        if not unpaid:
            return {"text": "You have no unpaid bills. You're all settled up! ✅", "data": {}}
        total = sum(b["amount"] for b in unpaid)
        lines = "\n".join(f"- Bill #{b['bill_id']}: {b['description']} — ₹{b['amount']:.2f} ([View Invoice](/billing/invoice/{b['bill_id']}))" for b in unpaid)
        bills_url = f"/bills?patient_id={patient_id}"
        report_url = f"/patient/{patient_id}/report"
        msg = (
            f"You have {len(unpaid)} unpaid bill(s) totalling ₹{total:.2f}:\n\n{lines}\n\n"
            f"💳 **Pay Dues**: [Click here to Pay Pending Bills]({bills_url})\n"
            f"📄 **Full Health & Billing Report**: [View & Download Report]({report_url})"
        )
        return {"text": msg, "data": {"bills": unpaid}}

    # Billing HISTORY / breakdown / "how much have I paid" style queries -
    # a richer view than the plain bill list below: category-wise totals
    # (consultation, lab, pharmacy, other) plus the payment ledger.
    history_phrases = (
        "billing history", "payment history", "past bills", "previous bills",
        "past payments", "previous payments", "breakdown", "how much have i paid",
        "how much did i pay", "total bill", "total charges", "all my charges",
        "consultation fee", "lab charges", "medicine charges", "full bill",
        "billing summary", "payment summary", "paid so far", "spent on",
    )
    if any(p in lower for p in history_phrases):
        bills = query("SELECT * FROM bills WHERE patient_id = ? ORDER BY date_issued DESC", (patient_id,))
        if not bills:
            return {"text": "You don't have any billing history on record yet.", "data": {}}

        breakdown = {"consultation": 0.0, "lab": 0.0, "pharmacy": 0.0, "other": 0.0}
        for b in bills:
            cat = b["category"] if b["category"] in breakdown else "other"
            breakdown[cat] += b["amount"]
        total_billed = sum(breakdown.values())

        payments = query(
            """SELECT p.*, b.description as bill_description FROM payments p
               JOIN bills b ON p.bill_id = b.bill_id
               WHERE p.patient_id = ? ORDER BY p.paid_at DESC""",
            (patient_id,),
        )
        total_paid = sum(p["amount_paid"] for p in payments)
        total_unpaid = sum(b["amount"] for b in bills if b["status"] == "unpaid")

        msg = (
            "Here's your billing history:\n\n"
            f"- **Consultation fees**: ₹{breakdown['consultation']:.2f}\n"
            f"- **Lab charges**: ₹{breakdown['lab']:.2f}\n"
            f"- **Medicine/Pharmacy charges**: ₹{breakdown['pharmacy']:.2f}\n"
            f"- **Other charges**: ₹{breakdown['other']:.2f}\n\n"
            f"**Total billed**: ₹{total_billed:.2f} | **Total paid**: ₹{total_paid:.2f} | "
            f"**Outstanding**: ₹{total_unpaid:.2f}\n\n"
        )
        if payments:
            recent = "\n".join(
                f"- {p['paid_at']}: ₹{p['amount_paid']:.2f} for {p['bill_description']} ({p['payment_method']})"
                for p in payments[:5]
            )
            msg += f"Recent payments:\n{recent}\n\n"
        msg += "You can see the full breakdown and pay any pending bills from the Billing page in your dashboard."
        return {"text": msg, "data": {"bills": bills, "breakdown": breakdown, "payments": payments}}

    bills = query("SELECT * FROM bills WHERE patient_id = ? ORDER BY date_issued DESC", (patient_id,))
    if not bills:
        return {"text": "You don't have any bills on record yet.", "data": {}}
    lines = []
    for b in bills:
        ins = f", insurance: {b['insurance_provider']}" if b["insurance_covered"] else ""
        lines.append(f"- Bill #{b['bill_id']} ({b['date_issued']}): {b['description']} — ₹{b['amount']:.2f} "
                     f"[{b['status']}]{ins}")
    return {"text": "Here's your billing summary:\n\n" + "\n".join(lines), "data": {"bills": bills}}
