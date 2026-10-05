"""
Orchestrator Agent
------------------
The central brain of MediAssist AI. For every incoming chat message it:

  1. Runs the full NLP pipeline (tokenization, stopword removal,
     stemming, lemmatization, POS tagging) for transparency/demo.
  2. Extracts entities (spaCy NER + hospital-domain dictionary
     matching: doctors, departments, medicines, symptoms, dates,
     emergency signals).
  3. Runs sentiment analysis.
  4. Classifies intent using the TF-IDF + ML classifier.
  5. SAFETY OVERRIDE: if emergency signals are detected, routes
     straight to the Emergency Agent regardless of the classified
     intent or any in-progress conversation.
  6. Resolves references using conversation context (e.g. "book Arun"
     right after "I need a heart doctor").
  7. Dispatches to the correct specialized agent and returns a
     structured response including everything needed for the
     chatbot UI's debug panel (intent, entities, sentiment, agent,
     confidence).
"""
from database.db import query
from nlp import preprocessor, ner, sentiment as sentiment_mod, intent_classifier, context_manager as ctx_mgr
from agents import (
    doctor_agent, appointment_agent, department_agent, lab_agent, pharmacy_agent,
    patient_agent, billing_agent, triage_agent, emergency_agent, faq_agent,
)

_SMALL_TALK_RESPONSES = {
    "greeting": "Hello! 👋 I'm MediAssist AI, your hospital assistant. I can help you find "
                "doctors, book appointments, check lab reports, answer questions about our "
                "departments, pharmacy, billing, and more. How can I help you today?",
    "thanks": "You're very welcome! Is there anything else I can help you with?",
    "goodbye": "Take care, and don't hesitate to come back if you need anything else. Wishing "
               "you good health! 👋",
}

_AGENT_DISPATCH = {
    "DoctorAgent": doctor_agent,
    "AppointmentAgent": appointment_agent,
    "DepartmentAgent": department_agent,
    "LabAgent": lab_agent,
    "PharmacyAgent": pharmacy_agent,
    "PatientAgent": patient_agent,
    "BillingAgent": billing_agent,
    "TriageAgent": triage_agent,
    "EmergencyAgent": emergency_agent,
    "FAQAgent": faq_agent,
}


def _load_reference_lists():
    doctors = query("SELECT * FROM doctors")
    departments = query("SELECT * FROM departments")
    medicines = query("SELECT * FROM medicines")
    return doctors, departments, medicines


def _log_chat(user_id, session_id, user_message, bot_response, intent, agent, confidence, sentiment_label,
              entities, input_mode="text", lang="en"):
    import json as _json
    query(
        """INSERT INTO chat_logs (user_id, session_id, user_message, bot_response, intent, agent,
           confidence, sentiment, entities, input_mode, lang) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (user_id, session_id, user_message, bot_response, intent, agent, confidence, sentiment_label,
         _json.dumps(entities), input_mode, lang),
        commit=True,
    )


def get_chat_history(user_id=None, session_id=None, limit=50):
    """
    Returns recent chat turns for the chat-history panel, newest first.
    Scoped to the logged-in user when available, otherwise falls back
    to the current browser session so guests still see their own
    conversation history.
    """
    if user_id:
        rows = query(
            "SELECT * FROM chat_logs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
    else:
        rows = query(
            "SELECT * FROM chat_logs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
    return rows or []


def process_message(text: str, session_id: str, user=None, input_mode="text", lang="en") -> dict:
    """
    Main entry point called by the /api/chat route.
    `user` is a dict of the logged-in user (or None for guests).
    """
    text = text.strip()
    if not text:
        return {
            "response": "I didn't quite catch that — could you type your question?",
            "intent": "unknown", "agent": "OrchestratorAgent", "confidence": 0.0,
            "sentiment": {"label": "Neutral", "compound": 0}, "entities": {}, "nlp_pipeline": {},
        }

    # 1) NLP preprocessing pipeline (for transparency / NLP demo panel)
    nlp_steps = preprocessor.full_pipeline(text)

    # 2) Entities
    doctors_ref, departments_ref, medicines_ref = _load_reference_lists()
    entities = ner.extract_all_entities(text, doctors_ref, departments_ref, medicines_ref)

    # 3) Sentiment
    sentiment_result = sentiment_mod.analyze_sentiment(text)

    # 4) Intent classification
    intent_result = intent_classifier.predict_intent(text)
    intent = intent_result["intent"]
    agent_name = intent_result["agent"]
    confidence = intent_result["confidence"]

    # 5) SAFETY OVERRIDE - emergency detection always wins
    is_emergency = bool(entities.get("emergency_signals")) or intent == "emergency"
    if is_emergency:
        agent_name = "EmergencyAgent"
        intent = "emergency"
        confidence = max(confidence, 95.0)

    # 6) Continue an in-progress multi-turn flow - but only if this message
    #    plausibly continues it (has the slot we're waiting for, or is
    #    itself an appointment-related intent). Anything else (a fresh
    #    question, an emergency, etc.) abandons the pending flow instead
    #    of hijacking unrelated messages.
    ctx = ctx_mgr.get_context(session_id)
    if is_emergency and ctx.pending_action:
        ctx_mgr.clear_pending_action(session_id)
    elif ctx.pending_action and ctx.pending_action.startswith("appointment_"):
        has_date = bool(entities.get("dates"))
        has_doctor = bool(entities.get("doctors"))
        is_appointment_intent = intent.startswith("appointment")
        plausibly_continues = is_appointment_intent or has_date or has_doctor

        if plausibly_continues:
            agent_name = "AppointmentAgent"
            intent = intent if intent.startswith("appointment") else "appointment_book"
        else:
            ctx_mgr.clear_pending_action(session_id)

    # 7) Handle simple small talk directly (no agent dispatch needed)
    if not is_emergency and intent in _SMALL_TALK_RESPONSES and not ctx.pending_action:
        bot_text = _SMALL_TALK_RESPONSES[intent]
        result = {"text": bot_text, "data": {}}
    else:
        resolved_doctors = ctx_mgr.resolve_doctor_reference(session_id, entities)
        resolved_department = ctx_mgr.resolve_department_reference(session_id, entities)

        agent_module = _AGENT_DISPATCH.get(agent_name, faq_agent)
        kwargs = dict(text=text, entities=entities, sentiment=sentiment_result, session_id=session_id, user=user)

        if agent_name in ("DoctorAgent",):
            kwargs["resolved_doctors"] = resolved_doctors
            kwargs["resolved_department"] = resolved_department
        elif agent_name in ("AppointmentAgent",):
            kwargs["resolved_doctors"] = resolved_doctors
            kwargs["resolved_department"] = resolved_department
        elif agent_name == "DepartmentAgent":
            kwargs["resolved_department"] = resolved_department
        elif agent_name == "PharmacyAgent":
            kwargs["resolved_medicines"] = entities.get("medicines")

        result = agent_module.handle(**kwargs)

    bot_text = result["text"]

    # 8) Update conversation context & log
    ctx_mgr.update_after_turn(session_id, text, bot_text, intent, agent_name, entities)
    _log_chat(
        user["user_id"] if user else None, session_id, text, bot_text, intent, agent_name,
        confidence, sentiment_result["label"], entities, input_mode=input_mode, lang=lang,
    )

    return {
        "response": bot_text,
        "intent": intent,
        "agent": agent_name,
        "confidence": confidence,
        "sentiment": sentiment_result,
        "entities": entities,
        "nlp_pipeline": nlp_steps,
        "data": result.get("data", {}),
        "is_emergency": result.get("is_emergency", False),
        "requires_login": result.get("requires_login", False),
    }
