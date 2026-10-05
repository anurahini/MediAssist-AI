"""
Pharmacy Agent
--------------
Answers questions about medicine availability, price and general
pharmacy information. Never gives dosage/prescribing advice — it only
reports catalog/stock data and reminds users that prescription-only
medicines require a doctor's prescription.
"""
from database.db import query

PHARMACY_INFO = {
    "location": "Ground Floor, near the Main Entrance",
    "timings": "Open 24 hours, 7 days a week",
    "contact": "+91-1800-123-4567 (ext. 100)",
}


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None,
           resolved_medicines=None) -> dict:
    lower = text.lower()

    if any(w in lower for w in ["where is the pharmacy", "pharmacy timing", "pharmacy location",
                                 "pharmacy hour", "pharmacy open", "pharmacy contact"]):
        msg = (f"🏥 Our in-house pharmacy is located at {PHARMACY_INFO['location']}.\n"
               f"🕐 Timings: {PHARMACY_INFO['timings']}\n"
               f"☎ Contact: {PHARMACY_INFO['contact']}")
        return {"text": msg, "data": PHARMACY_INFO}

    meds = resolved_medicines
    if not meds:
        all_meds = query("SELECT * FROM medicines")
        lower_words = lower.split()
        meds = [m for m in all_meds if m["name"].split()[0].lower() in lower]

    if meds:
        lines = []
        for m in meds:
            full = query("SELECT * FROM medicines WHERE medicine_id = ?", (m["medicine_id"],), fetchone=True)
            avail = "in stock" if full["stock_quantity"] > 0 else "out of stock"
            rx_note = " (requires a valid prescription)" if full["requires_prescription"] else ""
            lines.append(f"**{full['name']}** — ₹{full['price']:.2f}, {avail}{rx_note}. {full['description']}")
        return {"text": "Here's what I found:\n\n" + "\n\n".join(lines), "data": {"medicines": meds}}

    if "list" in lower or "what medicine" in lower or "available medicine" in lower:
        all_meds = query("SELECT name, price, category FROM medicines ORDER BY category")
        lines = "\n".join(f"- {m['name']} ({m['category']}) — ₹{m['price']:.2f}" for m in all_meds)
        return {"text": f"Here are the medicines available at our pharmacy:\n\n{lines}", "data": {"medicines": all_meds}}

    return {"text": "I can check medicine availability and prices, or share pharmacy timings and "
                     "location. Which medicine are you looking for? Note: I can't recommend or "
                     "prescribe medicines — please consult a doctor for that.", "data": {}}
