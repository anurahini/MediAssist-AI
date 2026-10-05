# 🏥 MediAssist AI — Multi-Agent Hospital Assistant Chatbot

MediAssist AI is a full-stack, multi-agent hospital assistant chatbot built for an
AI/NLP college project. A central **Orchestrator Agent** uses classic NLP techniques
(tokenization, stopword removal, stemming, lemmatization, POS tagging, Named Entity
Recognition, TF-IDF + Machine Learning intent classification, and sentiment analysis)
to understand natural-language questions and automatically route them to one of ten
specialized agents. The project also ships a full hospital dashboard (login,
appointments, lab reports, prescriptions, billing, pharmacy, admin panel, and an
NLP Demo page) built with Flask, SQLite, and vanilla HTML/CSS/JavaScript — **no
paid APIs are used anywhere in this project.**

---

## 🆕 New in this update: Emergency Alerts, Medical History & Billing History

- **Emergency Detection** — expanded keyword coverage (breathing difficulty,
  road/car accidents, profuse/excessive bleeding, losing consciousness,
  unresponsive, etc. in `nlp/ner.py`) on top of the existing safety-override
  in the Orchestrator (an emergency always wins, regardless of the classified
  intent or any in-progress conversation). The Chatbot page now also shows a
  dedicated, pulsing red **Emergency Alert banner** above the chat — with a
  tap-to-call helpline link and the Emergency Department location — in
  addition to the existing red-tinted emergency chat bubble.
- **Patient Medical History** — a new **Medical History** page
  (`/medical-history`, linked from the sidebar and dashboard) shows a single
  chronological timeline combining a patient's past appointments/doctor
  consultations (with symptoms/reason), prescriptions, and lab reports. The
  chatbot can now also answer natural questions like *"show my medical
  history"*, *"give me my full health record"*, or *"what happened in my past
  visits"* with the same combined summary.
- **Billing History** — bills now carry a `category` (consultation / lab /
  pharmacy / other), and a new `payments` table records every payment
  transaction. The Bills page shows a charges breakdown by category, total
  billed/paid/outstanding, and a full payment history table, alongside the
  existing bill list and "Pay Now" flow (which now also logs a payment
  record). The chatbot answers *"show my billing history"*, *"give me a
  breakdown of my charges"*, *"how much have I paid so far"*, etc. with the
  same breakdown.
- Richer sample data in `database/seed_data.py` (multiple past visits,
  prescriptions, lab reports, categorized bills, and payments per demo
  patient) so all three features have real history to show out of the box.
- 8 new automated tests covering all three features (57 total, all passing).

See the "Modified/Added Files" note at the end of this README for the full
list of files touched by this update.

---

## 🆕 What's new in this update

- **Doctor availability checking for bookings** — the Appointment Agent now
  validates the requested date against each doctor's `available_days`, and
  generates real 30-minute slots across their `available_time` window, checking
  existing confirmed/rescheduled appointments so two patients can never be
  double-booked into the same slot. If a doctor doesn't work that day, or is
  fully booked, the bot tells you and asks for a different date/doctor instead
  of silently overbooking.
- **Voice input (Speech-to-Text)** — a 🎤 mic button on the Chatbot page uses the
  browser's built-in Web Speech API to transcribe what you say directly into the
  chat box and send it automatically. Every transcript is recorded in a new
  `voice_logs` table.
- **Voice output (Text-to-Speech)** — a "🔊 Voice Reply" toggle reads the bot's
  replies aloud using the browser's built-in `speechSynthesis` API.
- **English ↔ Tamil translation** — a language selector on the Chatbot page lets
  you chat in Tamil; your message is translated to English for the NLP pipeline
  (via the free, keyless MyMemory translation API), and the bot's reply is
  translated back to Tamil for display and voice playback. The original English
  text is always shown as a small caption for transparency.
- **Chat History panel** — a "🕘 History" button on the Chatbot page opens a
  panel of your past conversation turns (pulled from the existing `chat_logs`
  table via a new `/api/chat/history` endpoint), including whether each message
  came from voice or text input.
- **Expanded training data** — every intent in `data/training_data.json` now has
  20–30 phrased examples (536 examples total across 25 intents, up from ~370),
  so more natural phrasings are classified correctly.

See the "Modified/Added Files" note at the end of this README for the full list
of files touched by this update.

---

## ✨ Key Features

- **Central Orchestrator Agent** — runs the full NLP pipeline on every message and
  routes it to the correct specialized agent.
- **10 Specialized Agents**: Doctor, Appointment, Department, Lab, Pharmacy, Patient,
  Billing, Triage, Emergency, FAQ.
- **Natural, contextual conversation** — e.g.
  > User: "I need a heart doctor."
  > Bot: "Sure, our Cardiology department has Dr. Arun and Dr. Priya."
  > User: "Book Arun tomorrow."
  > Bot understands "Arun" refers to the previously-mentioned doctor and books the
  > appointment.
- **Full NLP pipeline**: tokenization, stopword removal, stemming (Porter),
  lemmatization (WordNet), POS tagging, Named Entity Recognition (spaCy + hospital
  domain dictionaries), TF-IDF + Logistic Regression intent classification, and
  VADER-based sentiment analysis.
- **Safety-first design**: emergency symptoms (severe chest pain, difficulty
  breathing, unconsciousness, severe bleeding, etc.) are *always* detected and
  routed to the Emergency Agent, even mid-conversation, and the bot never
  diagnoses conditions or prescribes medicine.
- **Full hospital dashboard**: Login/Register, Chatbot, Doctors, Departments,
  Appointments, Lab Reports, Prescriptions, Bills, Pharmacy, Patient Profile,
  Admin Dashboard, and an NLP Demo page.
- **Realistic seeded data**: 12 departments, 17 doctors, 15 medicines, 15 lab
  tests, 15 FAQs, sample patients/appointments/bills/prescriptions/reports.
- **Secure authentication**: passwords hashed with Werkzeug's PBKDF2 hasher,
  session-based auth, per-patient data scoping (a patient can only ever see
  their own appointments/reports/bills/prescriptions).

---

## 🏗️ Architecture

```
User message
     │
     ▼
Orchestrator Agent  (agents/orchestrator.py)
     │  1. NLP preprocessing (tokenize, stopwords, stem, lemmatize, POS)
     │  2. Entity extraction (spaCy NER + hospital dictionaries + dates)
     │  3. Sentiment analysis (VADER + domain lexicon)
     │  4. Intent classification (TF-IDF + Logistic Regression)
     │  5. SAFETY OVERRIDE — emergency signals always win
     │  6. Conversation-context resolution (session-based)
     ▼
Dispatch to specialized agent
     │
     ├── DoctorAgent        — doctors, specializations, availability
     ├── AppointmentAgent   — book / cancel / reschedule / check appointments
     ├── DepartmentAgent    — departments, services, timings, locations
     ├── LabAgent           — tests, preparation, prices, report status
     ├── PharmacyAgent      — medicines, availability, pharmacy info
     ├── PatientAgent       — patient's own appointments/reports/prescriptions
     ├── BillingAgent       — bills, payments, insurance
     ├── TriageAgent        — maps symptoms → department (never diagnoses)
     ├── EmergencyAgent     — immediate emergency guidance (highest priority)
     └── FAQAgent           — hospital timings, facilities, parking, contact
     ▼
Structured JSON response (text + intent + agent + confidence + entities + sentiment)
     ▼
Chatbot UI renders the reply + a live "NLP Analysis" debug panel
```

---

## 📁 Project Structure

```
MediAssist-AI/
├── app.py                     # Flask application factory & entry point
├── requirements.txt
├── README.md
├── database/
│   ├── schema.sql              # SQLite schema (13 tables)
│   ├── db.py                   # Connection helper
│   └── seed_data.py            # Realistic sample data seeder
├── agents/
│   ├── orchestrator.py         # Central NLU + routing brain
│   ├── doctor_agent.py
│   ├── appointment_agent.py    # Multi-turn slot-filling booking flow
│   ├── department_agent.py
│   ├── lab_agent.py
│   ├── pharmacy_agent.py
│   ├── patient_agent.py
│   ├── billing_agent.py
│   ├── triage_agent.py
│   ├── emergency_agent.py      # Safety-critical, highest priority
│   └── faq_agent.py            # TF-IDF similarity FAQ matching
├── nlp/
│   ├── preprocessor.py         # Tokenize, stopwords, stem, lemmatize, POS
│   ├── ner.py                  # spaCy NER + hospital domain entities + dates
│   ├── sentiment.py             # VADER sentiment + domain lexicon
│   ├── intent_classifier.py     # TF-IDF + Logistic Regression
│   └── context_manager.py       # Multi-turn conversation memory
├── routes/                      # Flask blueprints (auth, chatbot, doctors, ...)
├── templates/                   # Jinja2 HTML templates
├── static/
│   ├── css/style.css            # Full design system
│   └── js/ (main.js, chatbot.js)
├── data/
│   └── training_data.json       # ~500 labeled examples across 25 intents
├── models/
│   └── intent_model.pkl         # Trained TF-IDF + LogisticRegression pipeline
└── tests/
    ├── test_chatbot.py          # 30 end-to-end chatbot test cases
    └── test_nlp.py               # 19 NLP pipeline unit tests
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
- Python 3.9+ (developed & tested on Python 3.12)
- pip

### 2. Clone / unzip the project
```bash
unzip MediAssist-AI.zip
cd MediAssist-AI
```

### 3. (Recommended) Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the application
```bash
python app.py
```
That's it. This project ships its own small `nltk_data/` folder (~17 MB,
English-only) so the NLTK tokenizer, stopwords, lemmatizer, POS tagger,
and VADER sentiment lexicon are already there — **no internet access is
needed at runtime for NLTK**, which also means no more failures on
locked-down networks (corporate proxies, antivirus, or Windows setups
that block NLTK's own download servers with errors like `WinError
10054`). The spaCy English model is installed automatically by step 4
above via its direct wheel URL in `requirements.txt`.

*(If you ever delete the bundled `nltk_data/` folder, the app will try
to re-download the same packages automatically, and if there's truly no
internet available it falls back to a simplified tokenizer/lemmatizer
so the chatbot still works — just with slightly less linguistic
normalization.)*

On first run, the app will automatically:
- Create the SQLite database (`database/mediassist.db`) from `schema.sql`
- Seed it with realistic sample data
- Train the TF-IDF intent classifier and save it to `models/intent_model.pkl`

Then open your browser at **http://127.0.0.1:5000**

### 6. Demo Login Credentials
| Role    | Username    | Password    |
|---------|-------------|-------------|
| Patient | `john_doe`  | `Passw0rd!` |
| Patient | `sara_p`    | `Passw0rd!` |
| Patient | `ravi_k`    | `Passw0rd!` |
| Admin   | `admin`     | `Passw0rd!` |

Or register a brand-new patient account from the **Register** page.

---

## 🧪 Running Tests

The project includes **49 automated tests** (30 chatbot end-to-end tests + 19 NLP
unit tests):

```bash
# Run everything
python -m pytest tests/ -v

# Run just the chatbot / agent-routing tests
python -m pytest tests/test_chatbot.py -v

# Run just the NLP pipeline unit tests
python -m pytest tests/test_nlp.py -v
```

Sample chatbot test cases (see `tests/test_chatbot.py` for all 30):

| # | User Message | Expected Agent |
|---|---------------|-----------------|
| 1 | "Hello" | OrchestratorAgent (small talk) |
| 2 | "I need a heart doctor" | DoctorAgent |
| 3 | "Book Arun tomorrow." (after the above) | AppointmentAgent (context resolved) |
| 4 | "Show my appointments" | AppointmentAgent |
| 5 | "Tell me about the cardiology department" | DepartmentAgent |
| 6 | "How much does an MRI cost?" | LabAgent |
| 7 | "Is my lab report ready?" | LabAgent |
| 8 | "Do you have paracetamol available?" | PharmacyAgent |
| 9 | "Show my prescriptions" | PatientAgent |
| 10 | "Show my bills" | BillingAgent |
| 11 | "I have a headache and mild fever" | TriageAgent |
| 12 | "I am having severe chest pain and can't breathe" | **EmergencyAgent** |
| 13 | "My father just collapsed and is unconscious" | **EmergencyAgent** |
| 14 | "What are the visiting hours?" | FAQAgent |
| 15 | "Is parking available?" | FAQAgent |

...plus tests for cancel/reschedule, multi-turn slot-filling, insurance queries,
sentiment detection, and NLP pipeline correctness.

---

## 🧠 The NLP Demo Page

Navigate to **NLP Demo** in the sidebar (or `/nlp-demo`) to type any sentence and
see, live:
1. Tokenization
2. Stopword removal
3. Porter Stemming
4. WordNet Lemmatization
5. POS Tagging
6. Named Entity Recognition (spaCy + hospital-domain entities: doctors,
   departments, medicines, symptoms, dates, emergency signals)
7. Sentiment Analysis (VADER + domain-tuned lexicon)
8. Intent Classification (TF-IDF + Logistic Regression, with top-3 candidates
   and confidence)

The chatbot page itself also shows a live "NLP Analysis" panel with **Detected
Intent, Selected Agent, Sentiment, Confidence, and Extracted Entities** for
every message — exactly matching the format requested for the project:

```
Intent: appointment_book
Entity: Dr Arun
Date: tomorrow
Agent: AppointmentAgent
Confidence: 94%
```

---

## 🔒 Authentication & Data Protection

- Passwords are hashed with Werkzeug's PBKDF2-based hasher — never stored in
  plain text.
- All patient-specific chatbot/API endpoints (appointments, lab reports,
  prescriptions, billing) require a logged-in session and are scoped strictly
  to that patient's own `patient_id` — no cross-patient data leakage.
- Session cookies are HTTP-only and `SameSite=Lax`.
- Admin-only routes (`/admin/*`) require the `admin` role.
- The chatbot **never diagnoses conditions or prescribes medicine or dosages**.
  The Triage Agent only ever suggests which *department* to visit. Emergency
  symptoms always trigger the Emergency Agent with clear, immediate guidance
  to seek professional care — it never tries to handle the situation itself.

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, Flask, Flask-CORS |
| Database | SQLite |
| NLP | NLTK (tokenization, stopwords, stemming, lemmatization, POS, VADER), spaCy (NER), scikit-learn (TF-IDF + Logistic Regression) |
| Frontend | HTML5, CSS3 (custom design system, no framework), vanilla JavaScript |
| Auth | Flask sessions + Werkzeug password hashing |
| Testing | pytest / unittest |

No paid or external APIs are used anywhere in this project — everything runs
fully locally/offline once the spaCy model and NLTK corpora are downloaded.

---

## 📌 Notes for Evaluators

- To see the multi-turn context example from the assignment exactly as
  specified, log in and open the Chatbot page, then type:
  1. `I need a heart doctor.`
  2. `Book Arun tomorrow.`

  The second message has no doctor name match on its own context-free —
  it resolves "Arun" via the conversation context set by the first message,
  then books the appointment and confirms it.

- To see the Emergency Agent safety override, type something like
  `I am having severe chest pain and can't breathe` at any point in the
  conversation (even mid-booking) — it will immediately override whatever
  else was happening and return emergency guidance.

- The intent classifier is retrainable at any time:
  ```bash
  python nlp/intent_classifier.py
  ```
  This retrains on `data/training_data.json` and overwrites
  `models/intent_model.pkl`.

- To reset the database back to the original sample data, simply delete
  `database/mediassist.db` (and `database/.secret_key` if you also want a
  fresh session secret) and restart the app — it will reseed automatically.

---

## 📄 License

Built for educational / academic purposes as part of an AI/NLP college
project. Free to use, modify and extend.

---

## 🩹 Bug-fix update (this pass)

This round of changes fixed three real problems without touching any UI,
route, or existing feature:

1. **The app crashed on every single chat message on a fresh install,**
   and on some networks kept failing even after retries. NLTK needs
   several data packages (tokenizer, wordnet, POS tagger, VADER lexicon)
   downloaded separately from the library, and only `stopwords` was
   being auto-downloaded. On networks that block NLTK's download
   servers entirely (common with corporate proxies/antivirus — this
   shows up as `WinError 10054` on Windows), even the fallback download
   attempt failed. **Fix:** the required NLTK data is now bundled directly
   in the project (`nltk_data/`, English-only, ~17 MB) and loaded from
   disk — no network call needed at all in the normal case.
2. **Voice input silently failed if served over plain HTTP** (browsers
   only allow microphone access on HTTPS or localhost), and speech
   recognition errors (permission denied, no microphone, no speech
   detected, network drop) all produced the same unhelpful behavior.
3. **A bug anywhere in the NLP/agent pipeline surfaced as a raw 500
   error** instead of a graceful chatbot reply.

### What changed
- **`nltk_data/`** (new) — bundled English-only NLTK data (tokenizer,
  stopwords, wordnet, POS tagger, VADER lexicon) so the app runs fully
  offline for NLTK out of the box.
- `nlp/preprocessor.py`, `nlp/sentiment.py` — load NLTK data from the
  bundled folder first; only attempt a network download if that folder
  is missing, and fall back to simplified logic (regex tokenizer, skip
  lemmatization, keyword-based sentiment) if that also fails, so the
  app never crashes.
- `nlp/ner.py` — falls back to a blank spaCy pipeline (no generic NER) if
  the English model can't load/download, while all hospital-domain entity
  matching (doctors, departments, medicines, symptoms, emergencies, dates)
  keeps working regardless.
- `requirements.txt` — the spaCy English model wheel is now installed
  automatically by `pip install -r requirements.txt` (previously a
  separate manual command), using the same network path that already
  works for your other Python packages.
- `app.py` — added an explicit "preparing NLP resources" startup step.
- `routes/chatbot.py` — wrapped `/api/chat` in a try/except safety net so
  any unexpected error returns a friendly chatbot message instead of a
  raw 500.
- `static/js/chatbot.js` — mic button now detects insecure (non-HTTPS)
  contexts and explains why voice won't work there, gives a specific
  message per speech-recognition error type, and recovers from
  double-click/invalid-state errors. The existing "auto-send transcribed
  text" behavior is unchanged — it just works reliably now that the
  backend no longer crashes.
- `README.md` — this note; setup no longer requires the old manual
  spaCy/NLTK download steps.

Verified with the project's own test suite (`pytest tests/ -v` → 49/49
passing) plus manual end-to-end runs of doctor search, department
timings, appointment booking/cancellation, lab reports, pharmacy,
billing, prescriptions, and the emergency safety override — all in
natural, non-scripted phrasing, and re-verified again with the
machine's own `nltk_data` cache removed entirely to confirm the bundled
copy alone is sufficient.

---

## 🗂 Modified / Added Files In This Update

| File | Change |
|------|--------|
| `database/schema.sql` | Added `voice_logs` table; added `input_mode` and `lang` columns to `chat_logs`. |
| `database/db.py` | Added a migration helper (`_ensure_columns`) so existing databases pick up new columns safely on startup. |
| `agents/orchestrator.py` | `process_message` now accepts/logs `input_mode` and `lang`; added `get_chat_history()` helper. |
| `agents/appointment_agent.py` | Booking now checks doctor weekly availability (`available_days`) and generates a real slot grid to avoid double-booking; clear messages when a doctor is off that day or fully booked. |
| `routes/chatbot.py` | Added `/api/chat/history` and `/api/voice-log` endpoints; `/api/chat` now accepts `input_mode`/`lang`. |
| `data/training_data.json` | Expanded every intent to 20–30 examples (536 total). |
| `models/intent_model.pkl` | Retrained on the expanded training data. |
| `templates/chatbot.html` | Added mic button, voice-reply toggle, language selector, and chat-history panel UI. |
| `static/js/chatbot.js` | Added Speech-to-Text, Text-to-Speech, EN↔TA translation (client-side, free MyMemory API), and history-panel logic. |
| `static/css/style.css` | Added styles for the new toolbar, mic button, and history panel. |
| `README.md` | This changelog + feature notes. |

No other files were changed — all existing routes, templates, agents, and tests
are untouched and the full 49-test suite (`tests/test_chatbot.py` +
`tests/test_nlp.py`) still passes.

---

## 🗂 Modified / Added Files — Emergency Alerts, Medical History & Billing History

| File | Change |
|------|--------|
| `nlp/ner.py` | Expanded `_EMERGENCY_KEYWORDS` (breathing difficulty, road/car accident, profuse/excessive bleeding, losing consciousness, unresponsive, severe injury, etc.). |
| `templates/chatbot.html` | Added the Emergency Alert banner markup (icon, message, tap-to-call link, department location, dismiss button). |
| `static/css/style.css` | Added `.emergency-alert` styles + pulsing animation. |
| `static/js/chatbot.js` | Shows/hides the Emergency Alert banner based on `data.is_emergency`; populates the helpline/location from the response; hides it on conversation reset. |
| `database/schema.sql` | Added `bills.category` column; added new `payments` table (payment-transaction ledger). |
| `database/db.py` | Migration for the new `bills.category` column via the existing `_ensure_columns` helper. |
| `database/seed_data.py` | Added multiple past visits per demo patient with linked prescriptions, lab reports, categorized bills, and payment records, so Medical History and Billing History have real data out of the box. |
| `routes/patient.py` | New `/medical-history` route: builds a combined, chronological timeline of appointments, prescriptions, and lab reports for the logged-in patient. |
| `templates/medical_history.html` | New page rendering that timeline, plus a quick patient-info summary (blood group, DOB, gender, emergency contact). |
| `templates/base.html` | Added a "🗂 Medical History" sidebar nav link. |
| `templates/dashboard.html` | Added a "🗂 Medical History" quick link. |
| `agents/patient_agent.py` | Added a combined medical-history summary handler, triggered by natural phrasings ("show my medical history", "give me my full health record", "what happened in my past visits", etc.). |
| `routes/billing.py` | `bills_page` now computes a category breakdown (consultation/lab/pharmacy/other) and fetches the payment history; `pay_bill` now also inserts a `payments` record. |
| `templates/bills.html` | Added a stats row (outstanding / total billed / total paid / breakdown) and a Payment History table, alongside the existing bill list and Pay Now button. |
| `agents/billing_agent.py` | Added a billing-history handler (category breakdown + recent payments), triggered by natural phrasings ("billing history", "breakdown of my charges", "how much have I paid so far", etc.). |
| `data/training_data.json` | Added disambiguating phrasings to `billing_payment`, `billing_inquiry`, and `patient_reports` so history-style questions route to the right agent instead of being confused with "thanks" or crossing between Patient/Billing agents. |
| `models/intent_model.pkl` | Retrained on the updated training data. |
| `tests/test_chatbot.py` | Added 8 new tests covering emergency keyword expansion, medical history (chatbot + page), and billing history (chatbot + page). |
| `README.md` | This changelog. |

No existing feature, route, template, or UI element was removed. Full test
suite: **57/57 passing** (49 original + 8 new).

