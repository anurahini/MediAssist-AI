"""
Chatbot routes: renders the chat UI and exposes the /api/chat endpoint
that the frontend JS calls for every message. Also exposes a session
reset endpoint used by the "New Conversation" button, a chat-history
endpoint for the History panel, and a voice-log endpoint that records
speech-to-text transcripts used to drive the chat.
"""
import logging
import os
import tempfile
import uuid
from flask import Blueprint, render_template, request, jsonify, session

from agents.orchestrator import process_message, get_chat_history
from database.db import query
from nlp import context_manager as ctx_mgr
from routes.auth import get_current_user

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint("chatbot", __name__)


@chatbot_bp.route("/chatbot")
def chatbot_page():
    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid.uuid4())
    user = get_current_user()
    return render_template("chatbot.html", user=user)


@chatbot_bp.route("/api/chat", methods=["POST"])
def api_chat():
    payload = request.get_json(silent=True) or {}
    message = payload.get("message", "")
    input_mode = payload.get("input_mode", "text")
    lang = payload.get("lang", "en")
    if input_mode not in ("text", "voice"):
        input_mode = "text"

    if "chat_session_id" not in session:
        session["chat_session_id"] = str(uuid.uuid4())
    session_id = session["chat_session_id"]

    user = get_current_user()
    try:
        result = process_message(message, session_id, user, input_mode=input_mode, lang=lang)
    except Exception:
        # Safety net: a bug in any one agent should never surface as a
        # raw 500 / "something went wrong" in the UI. Log it server-side
        # for debugging and answer with a graceful, on-brand fallback so
        # the conversation can continue.
        logger.exception("api_chat: process_message failed for message=%r", message)
        result = {
            "response": "Sorry, I had trouble understanding that one. Could you rephrase it, or "
                        "try asking about doctors, appointments, departments, lab reports, "
                        "pharmacy, billing, or hospital timings?",
            "intent": "unknown", "agent": "OrchestratorAgent", "confidence": 0.0,
            "sentiment": {"label": "Neutral", "compound": 0}, "entities": {}, "nlp_pipeline": {},
            "data": {}, "is_emergency": False, "requires_login": False,
        }
    return jsonify(result)


@chatbot_bp.route("/api/chat/reset", methods=["POST"])
def api_chat_reset():
    session_id = session.get("chat_session_id")
    if session_id:
        ctx_mgr.reset_session(session_id)
    session["chat_session_id"] = str(uuid.uuid4())
    return jsonify({"status": "reset", "session_id": session["chat_session_id"]})


@chatbot_bp.route("/api/chat/history", methods=["GET"])
def api_chat_history():
    """Return the recent chat turns for the History panel."""
    user = get_current_user()
    session_id = session.get("chat_session_id")
    rows = get_chat_history(user_id=user["user_id"] if user else None, session_id=session_id, limit=50)
    # Oldest-first so the panel reads top-to-bottom like a transcript.
    rows = list(reversed(rows))
    history = [
        {
            "log_id": r["log_id"],
            "user_message": r["user_message"],
            "bot_response": r["bot_response"],
            "intent": r["intent"],
            "agent": r["agent"],
            "input_mode": r["input_mode"] if "input_mode" in r.keys() else "text",
            "created_at": r["created_at"],
        }
        for r in rows
    ]
    return jsonify({"history": history})


@chatbot_bp.route("/api/voice-log", methods=["POST"])
def api_voice_log():
    """
    Records a speech-to-text transcript captured by the browser's Web
    Speech API before it is sent through /api/chat. Purely for
    analytics/audit of the voice-input feature.
    """
    payload = request.get_json(silent=True) or {}
    transcript = (payload.get("transcript") or "").strip()
    recognition_lang = payload.get("recognition_lang", "en-US")
    if not transcript:
        return jsonify({"status": "skipped"}), 200

    user = get_current_user()
    session_id = session.get("chat_session_id")
    query(
        "INSERT INTO voice_logs (user_id, session_id, transcript, recognition_lang, used_for_chat) "
        "VALUES (?,?,?,?,1)",
        (user["user_id"] if user else None, session_id, transcript, recognition_lang),
        commit=True,
    )
    return jsonify({"status": "logged"})


@chatbot_bp.route("/api/voice-recognize", methods=["POST"])
def api_voice_recognize():
    """
    Server-side audio transcription backup endpoint. Accepts WAV/WebM audio blobs,
    transcribes via speech_recognition, logs event, and returns JSON transcript.
    """
    if "audio" not in request.files:
        return jsonify({"status": "error", "error": "No audio file provided", "transcript": ""}), 400

    audio_file = request.files["audio"]
    lang = request.form.get("lang", "en-US")

    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            audio_file.save(tmp.name)
            tmp_path = tmp.name

        try:
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
                transcript = recognizer.recognize_google(audio_data, language=lang)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

        if transcript:
            user = get_current_user()
            session_id = session.get("chat_session_id")
            query(
                "INSERT INTO voice_logs (user_id, session_id, transcript, recognition_lang, used_for_chat) "
                "VALUES (?,?,?,?,1)",
                (user["user_id"] if user else None, session_id, transcript, lang),
                commit=True,
            )
            return jsonify({"status": "success", "transcript": transcript})
        else:
            return jsonify({"status": "empty", "transcript": ""})
    except Exception as e:
        logger.warning(f"api_voice_recognize exception: {e}")
        return jsonify({"status": "error", "error": str(e), "transcript": ""}), 200
