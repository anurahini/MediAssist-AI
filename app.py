"""
MediAssist AI - Multi-Agent Hospital Assistant Chatbot
========================================================
Main Flask application entry point.

Run with:
    python app.py

The app will:
  1. Initialize the SQLite database (create tables if missing).
  2. Seed sample data on first run only.
  3. Train / load the TF-IDF intent classifier.
  4. Register all blueprints (auth, chatbot, doctors, departments,
     appointments, lab, pharmacy, patient, billing, admin, nlp_demo).
  5. Start the development server.
"""
import os
import secrets
from flask import Flask, render_template
from flask_cors import CORS

from database.db import init_db, DB_PATH


def create_app():
    app = Flask(__name__)
    CORS(app, supports_credentials=True)

    secret_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", ".secret_key")
    if os.path.exists(secret_key_path):
        with open(secret_key_path, "r") as f:
            app.secret_key = f.read().strip()
    else:
        key = secrets.token_hex(32)
        with open(secret_key_path, "w") as f:
            f.write(key)
        app.secret_key = key

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB

    # ---- Database bootstrap -------------------------------------------------
    first_time = init_db()
    if first_time:
        from database.seed_data import seed
        seed()

    # ---- Prepare NLP resources -------------------------------------------
    # Importing these modules triggers their one-time download of NLTK
    # data (tokenizer, stopwords, wordnet, POS tagger, VADER lexicon) and
    # the spaCy English model. Doing this explicitly, with a clear
    # message, means a first-time run downloads everything up front
    # instead of failing silently on the first chat message.
    print(" Preparing NLP resources (first run may take a moment)...")
    from nlp import preprocessor, sentiment as _sentiment, ner as _ner, intent_classifier
    intent_classifier._get_pipeline()
    print(" NLP resources ready.")

    # ---- Register blueprints --------------------------------------------------
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.chatbot import chatbot_bp
    from routes.doctors import doctors_bp
    from routes.departments import departments_bp
    from routes.appointments import appointments_bp
    from routes.lab import lab_bp
    from routes.pharmacy import pharmacy_bp
    from routes.patient import patient_bp
    from routes.billing import billing_bp
    from routes.admin import admin_bp
    from routes.nlp_demo import nlp_demo_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chatbot_bp)
    app.register_blueprint(doctors_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(lab_bp)
    app.register_blueprint(pharmacy_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(nlp_demo_bp)

    # ---- Error handlers ---------------------------------------------------
    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    # ---- Inject current_user into every template ---------------------------
    @app.context_processor
    def inject_user():
        from routes.auth import get_current_user
        return {"current_user": get_current_user()}

    return app


app = create_app()

if __name__ == "__main__":
    print("=" * 70)
    print(" MediAssist AI - Multi-Agent Hospital Assistant Chatbot")
    print(" Database:", DB_PATH)
    print(" Visit:    http://127.0.0.1:5000")
    print(" Demo login -> username: john_doe | password: Passw0rd!")
    print(" Admin login -> username: admin   | password: Passw0rd!")
    print("=" * 70)
    app.run(debug=True, host="0.0.0.0", port=5000)
