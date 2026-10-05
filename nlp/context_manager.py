"""
Conversation Context Manager for MediAssist AI.

Keeps a lightweight, per-session memory of the conversation so the
chatbot can resolve references such as:

    User: "I need a heart doctor."
    Bot:  "Cardiology has Dr. Arun and Dr. Priya."
    User: "Book Arun tomorrow."   <- "Arun" resolved via last mentioned
                                     doctors, "book" continues the flow
                                     into the AppointmentAgent.

Context is stored in-memory keyed by session_id (per browser tab /
login session). This is sufficient for a college project demo; a
production system would back this with Redis or a DB table.
"""
import time
from collections import deque

_MAX_TURNS = 8
_SESSION_TTL_SECONDS = 60 * 60  # 1 hour


class SessionContext:
    def __init__(self):
        self.turns = deque(maxlen=_MAX_TURNS)
        self.last_doctors = []          # list of doctor dicts recently mentioned
        self.last_department = None     # department dict recently mentioned
        self.last_intent = None
        self.last_agent = None
        self.pending_action = None      # e.g. "awaiting_appointment_date"
        self.pending_data = {}          # partial slots collected across turns
        self.updated_at = time.time()

    def touch(self):
        self.updated_at = time.time()


_STORE = {}


def get_context(session_id: str) -> SessionContext:
    _cleanup_expired()
    if session_id not in _STORE:
        _STORE[session_id] = SessionContext()
    ctx = _STORE[session_id]
    ctx.touch()
    return ctx


def _cleanup_expired():
    now = time.time()
    expired = [sid for sid, ctx in _STORE.items() if now - ctx.updated_at > _SESSION_TTL_SECONDS]
    for sid in expired:
        del _STORE[sid]


def update_after_turn(session_id: str, user_message: str, bot_response: str,
                       intent: str, agent: str, entities: dict):
    ctx = get_context(session_id)
    ctx.turns.append({"user": user_message, "bot": bot_response, "intent": intent, "agent": agent})
    ctx.last_intent = intent
    ctx.last_agent = agent

    if entities.get("doctors"):
        ctx.last_doctors = entities["doctors"]
    if entities.get("departments"):
        ctx.last_department = entities["departments"][0]

    ctx.touch()


def resolve_doctor_reference(session_id: str, entities: dict):
    """
    If the current message didn't explicitly mention a doctor but the
    previous turn(s) did, fall back to that doctor - this is what lets
    "Book Arun tomorrow" work right after "I need a heart doctor".
    """
    if entities.get("doctors"):
        return entities["doctors"]
    ctx = get_context(session_id)
    return ctx.last_doctors


def resolve_department_reference(session_id: str, entities: dict):
    if entities.get("departments"):
        return entities["departments"][0]
    ctx = get_context(session_id)
    return ctx.last_department


def set_pending_action(session_id: str, action: str, data: dict = None):
    ctx = get_context(session_id)
    ctx.pending_action = action
    ctx.pending_data = data or {}
    ctx.touch()


def clear_pending_action(session_id: str):
    ctx = get_context(session_id)
    ctx.pending_action = None
    ctx.pending_data = {}
    ctx.touch()


def get_history(session_id: str):
    ctx = get_context(session_id)
    return list(ctx.turns)


def reset_session(session_id: str):
    if session_id in _STORE:
        del _STORE[session_id]
