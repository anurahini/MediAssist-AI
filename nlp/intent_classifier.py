"""
Intent classification for MediAssist AI using TF-IDF vectorization +
a scikit-learn Logistic Regression classifier (chosen over a plain
SVM because it exposes calibrated predict_proba scores that we surface
to the user as a confidence percentage).

The trained pipeline is persisted to models/intent_model.pkl so the
Flask app doesn't need to retrain on every restart. Run this file
directly to (re)train:

    python nlp/intent_classifier.py
"""
import os
import json
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from nlp.preprocessor import normalize_for_model

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "training_data.json")
MODEL_PATH = os.path.join(BASE_DIR, "models", "intent_model.pkl")

# Maps each fine-grained intent label to the specialized agent responsible
# for handling it. Used by the Orchestrator Agent for routing.
INTENT_TO_AGENT = {
    "greeting": "OrchestratorAgent",
    "thanks": "OrchestratorAgent",
    "goodbye": "OrchestratorAgent",
    "doctor_search": "DoctorAgent",
    "doctor_availability": "DoctorAgent",
    "appointment_book": "AppointmentAgent",
    "appointment_cancel": "AppointmentAgent",
    "appointment_reschedule": "AppointmentAgent",
    "appointment_check": "AppointmentAgent",
    "department_info": "DepartmentAgent",
    "department_timings": "DepartmentAgent",
    "department_location": "DepartmentAgent",
    "lab_test_info": "LabAgent",
    "lab_report_status": "LabAgent",
    "pharmacy_medicine_search": "PharmacyAgent",
    "pharmacy_info": "PharmacyAgent",
    "patient_appointments": "PatientAgent",
    "patient_reports": "PatientAgent",
    "patient_prescriptions": "PatientAgent",
    "billing_inquiry": "BillingAgent",
    "billing_payment": "BillingAgent",
    "insurance_inquiry": "BillingAgent",
    "symptom_triage": "TriageAgent",
    "emergency": "EmergencyAgent",
    "faq": "FAQAgent",
}


def _load_training_data():
    with open(DATA_PATH, "r") as f:
        raw = json.load(f)
    texts, labels = [], []
    for intent, examples in raw.items():
        for ex in examples:
            texts.append(normalize_for_model(ex))
            labels.append(intent)
    return texts, labels


def train_model(save=True):
    texts, labels = _load_training_data()

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, C=8.0, class_weight="balanced")),
    ])
    pipeline.fit(texts, labels)

    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        joblib.dump(pipeline, MODEL_PATH)
    return pipeline


_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    if os.path.exists(MODEL_PATH):
        _pipeline = joblib.load(MODEL_PATH)
    else:
        _pipeline = train_model(save=True)
    return _pipeline


def predict_intent(text: str) -> dict:
    """
    Predict the intent of a user message.
    Returns: {intent, agent, confidence, top_intents:[{intent,confidence}]}
    """
    pipeline = _get_pipeline()
    normalized = normalize_for_model(text)

    if not normalized.strip():
        return {"intent": "unknown", "agent": "FAQAgent", "confidence": 0.0, "top_intents": []}

    probs = pipeline.predict_proba([normalized])[0]
    classes = pipeline.classes_
    ranked = sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)

    top_intent, top_conf = ranked[0]
    agent = INTENT_TO_AGENT.get(top_intent, "FAQAgent")

    return {
        "intent": top_intent,
        "agent": agent,
        "confidence": round(float(top_conf) * 100, 2),
        "top_intents": [{"intent": i, "confidence": round(float(c) * 100, 2)} for i, c in ranked[:3]],
    }


if __name__ == "__main__":
    model = train_model(save=True)
    print("Intent classifier trained and saved to:", MODEL_PATH)
    tests = [
        "I need a heart doctor",
        "book arun tomorrow",
        "I am having severe chest pain",
        "what are the visiting hours",
        "is my lab report ready",
    ]
    for t in tests:
        print(t, "->", predict_intent(t))
