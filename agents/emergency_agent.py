"""
Emergency Agent
---------------
Highest priority agent in the system. Triggered whenever the
Orchestrator (or the Triage Agent) detects emergency-level symptoms
such as severe chest pain, difficulty breathing, unconsciousness or
severe bleeding.

This agent NEVER diagnoses. Its only job is to:
  1. Immediately urge the user to seek emergency care / call emergency
     services.
  2. Surface the hospital's emergency contact details and the
     Emergency Medicine department location.
  3. Log the event so hospital staff could (in a real deployment) be
     alerted.
"""
from database.db import query

EMERGENCY_HELPLINE = "+91-1800-123-9999"
EMERGENCY_LOCATION = "Ground Floor, Main Entrance (Emergency Medicine Department)"


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None) -> dict:
    signals = entities.get("emergency_signals", [])

    message = (
        "🚨 This sounds like it could be a medical emergency. Please act immediately:\n\n"
        f"1. Call our 24x7 Emergency Helpline right now: **{EMERGENCY_HELPLINE}**\n"
        "2. Or call your local emergency number (e.g. 108 / 112) for an ambulance.\n"
        f"3. If you are already at the hospital, go directly to: **{EMERGENCY_LOCATION}**.\n\n"
        "I'm an assistant and can't diagnose or treat you, so please don't wait for a chat "
        "reply — get to emergency care or call for help now. If you are with the person, "
        "stay with them, keep them calm, and follow any instructions given by emergency "
        "responders on the phone."
    )

    dept = query(
        "SELECT * FROM departments WHERE name = 'Emergency Medicine'", fetchone=True
    )

    return {
        "text": message,
        "data": {
            "helpline": EMERGENCY_HELPLINE,
            "location": EMERGENCY_LOCATION,
            "detected_signals": signals,
            "department": dept,
        },
        "is_emergency": True,
    }
