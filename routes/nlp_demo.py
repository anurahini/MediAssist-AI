"""
NLP Demo page: lets a user (typically the professor/evaluator) type
any sentence and see every stage of the NLP pipeline used by the
chatbot - tokenization, stopword removal, stemming, lemmatization,
POS tagging, NER, sentiment analysis and intent classification -
displayed side by side.
"""
from flask import Blueprint, render_template, request, jsonify

from database.db import query
from nlp import preprocessor, ner, sentiment as sentiment_mod, intent_classifier
from routes.auth import login_required

nlp_demo_bp = Blueprint("nlp_demo", __name__)


@nlp_demo_bp.route("/nlp-demo")
@login_required
def nlp_demo_page():
    return render_template("nlp_demo.html")


@nlp_demo_bp.route("/api/nlp-demo", methods=["POST"])
@login_required
def nlp_demo_api():
    payload = request.get_json(silent=True) or {}
    text = payload.get("text", "").strip()
    if not text:
        return jsonify({"error": "Please enter some text."}), 400

    doctors = query("SELECT * FROM doctors")
    departments = query("SELECT * FROM departments")
    medicines = query("SELECT * FROM medicines")

    pipeline = preprocessor.full_pipeline(text)
    entities = ner.extract_all_entities(text, doctors, departments, medicines)
    sentiment_result = sentiment_mod.analyze_sentiment(text)
    intent_result = intent_classifier.predict_intent(text)

    return jsonify({
        "pipeline": pipeline,
        "entities": entities,
        "sentiment": sentiment_result,
        "intent": intent_result,
    })
