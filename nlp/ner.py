"""
Named Entity Recognition for MediAssist AI.

Combines:
  1. spaCy's pretrained statistical NER model (en_core_web_sm) for
     general entities such as PERSON, DATE, TIME, ORG, GPE.
  2. Custom dictionary/regex matchers built from the hospital database
     (doctor names, department names, symptom keywords, medicine names)
     since a generic model has no idea who "Dr. Arun" is.
  3. A relative-date resolver so "tomorrow" / "next monday" becomes an
     actual calendar date the Appointment Agent can use.
"""
import re
import spacy
from datetime import date, timedelta

# The hospital-specific entities below (doctors, departments, medicines,
# symptoms, emergency signals, dates) are plain dictionary/regex matching
# and never depend on spaCy, so they always work. spaCy's pretrained
# en_core_web_sm model only adds *generic* entities (PERSON/DATE/etc.)
# on top of that. If the model isn't installed and can't be downloaded
# (e.g. no internet on first run), we fall back to a blank pipeline
# instead of crashing the whole app - spacy_entities() will just return
# an empty list in that case.
try:
    _nlp = spacy.load("en_core_web_sm")
except OSError:
    try:
        from spacy.cli import download
        download("en_core_web_sm")
        _nlp = spacy.load("en_core_web_sm")
    except Exception:
        _nlp = spacy.blank("en")

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

_SYMPTOM_KEYWORDS = [
    "fever", "cough", "cold", "headache", "migraine", "chest pain", "back pain",
    "knee pain", "joint pain", "stomach pain", "abdominal pain", "nausea",
    "vomiting", "diarrhea", "rash", "itching", "allergy", "breathlessness",
    "shortness of breath", "dizziness", "fatigue", "sore throat", "toothache",
    "ear pain", "eye pain", "blurred vision", "high blood pressure", "diabetes",
    "chest discomfort", "palpitations", "swelling", "burning urination",
    "body ache", "weakness", "anxiety", "depression", "insomnia", "bleeding",
    "unconscious", "unconsciousness", "seizure", "fracture", "sprain", "burn",
    "difficulty breathing", "severe chest pain", "heart attack", "stroke",
]

_EMERGENCY_KEYWORDS = [
    "severe chest pain", "chest pain", "can't breathe", "cant breathe",
    "difficulty breathing", "breathing difficulty", "trouble breathing",
    "shortness of breath", "not breathing", "gasping for air",
    "unconscious", "unconsciousness", "unresponsive", "fainted", "collapsed",
    "passed out", "losing consciousness", "seizure", "convulsions",
    "severe bleeding", "heavy bleeding", "bleeding heavily", "profuse bleeding",
    "excessive bleeding", "heart attack", "stroke", "suicide", "overdose",
    "poisoning", "choking", "severe burn", "not responding", "accident",
    "road accident", "car accident", "trauma", "no pulse", "severe injury",
]


def _resolve_relative_date(phrase: str, base: date = None) -> str:
    """Convert a natural-language relative date phrase to YYYY-MM-DD."""
    base = base or date.today()
    phrase = phrase.lower().strip()

    if phrase in ("today", "now"):
        return base.isoformat()
    if phrase == "tomorrow":
        return (base + timedelta(days=1)).isoformat()
    if phrase in ("day after tomorrow", "day after"):
        return (base + timedelta(days=2)).isoformat()
    if phrase == "yesterday":
        return (base - timedelta(days=1)).isoformat()

    for i, day in enumerate(_WEEKDAYS):
        if day in phrase:
            days_ahead = (i - base.weekday() + 7) % 7
            if "next" in phrase or days_ahead == 0:
                days_ahead = days_ahead if days_ahead != 0 else 7
            return (base + timedelta(days=days_ahead)).isoformat()

    return None


def extract_dates(text: str):
    """Find relative/explicit date expressions in text."""
    found = []
    lower = text.lower()

    patterns = [
        r"day after tomorrow", r"tomorrow", r"today", r"yesterday",
        r"next\s+\w+day", r"this\s+\w+day",
        r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    ]
    for pat in patterns:
        for m in re.finditer(pat, lower):
            phrase = m.group()
            resolved = _resolve_relative_date(phrase)
            if not resolved and re.match(r"\d{4}-\d{2}-\d{2}", phrase):
                resolved = phrase
            found.append({"text": phrase, "resolved_date": resolved})
    return found


def extract_times(text: str):
    """Find time expressions e.g. '9 am', '14:00', 'morning'."""
    times = []
    for m in re.finditer(r"\b(\d{1,2})(:\d{2})?\s?(am|pm|AM|PM)\b", text):
        times.append(m.group().strip())
    for kw in ["morning", "afternoon", "evening", "night"]:
        if kw in text.lower():
            times.append(kw)
    return times


def extract_symptoms(text: str):
    lower = text.lower()
    return sorted(set(kw for kw in _SYMPTOM_KEYWORDS if kw in lower))


def extract_emergency_signals(text: str):
    lower = text.lower()
    return sorted(set(kw for kw in _EMERGENCY_KEYWORDS if kw in lower))


def extract_doctor_names(text: str, doctor_list):
    """
    Match doctor first/last names or full names against known doctors
    from the DB, tolerant of missing 'Dr.' prefix, e.g. "book Arun".
    """
    matches = []
    lower = text.lower()
    for doc in doctor_list:
        full_name = doc["full_name"]
        name_no_title = full_name.replace("Dr.", "").strip()
        parts = name_no_title.split()
        candidates = [full_name.lower(), name_no_title.lower()] + [p.lower() for p in parts if len(p) > 2]
        for cand in candidates:
            if re.search(r"\b" + re.escape(cand) + r"\b", lower):
                matches.append(doc)
                break
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for d in matches:
        if d["doctor_id"] not in seen:
            unique.append(d)
            seen.add(d["doctor_id"])
    return unique


def extract_department_names(text: str, department_list):
    lower = text.lower()
    matches = []
    for dept in department_list:
        if dept["name"].lower() in lower:
            matches.append(dept)
    return matches


def extract_medicine_names(text: str, medicine_list):
    lower = text.lower()
    matches = []
    for med in medicine_list:
        base_name = med["name"].split()[0].lower()  # e.g. "Paracetamol"
        if base_name in lower:
            matches.append(med)
    return matches


def spacy_entities(text: str):
    """Generic spaCy statistical NER (PERSON, DATE, TIME, ORG, GPE, etc.)"""
    doc = _nlp(text)
    return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]


def extract_all_entities(text: str, doctor_list=None, department_list=None, medicine_list=None) -> dict:
    """
    Master entity-extraction function combining spaCy NER with
    hospital-domain dictionary matching. Returns a structured dict
    ready to display in the chatbot debug panel / NLP demo page.
    """
    doctor_list = doctor_list or []
    department_list = department_list or []
    medicine_list = medicine_list or []

    return {
        "spacy_entities": spacy_entities(text),
        "dates": extract_dates(text),
        "times": extract_times(text),
        "symptoms": extract_symptoms(text),
        "emergency_signals": extract_emergency_signals(text),
        "doctors": [{"doctor_id": d["doctor_id"], "full_name": d["full_name"]} for d in extract_doctor_names(text, doctor_list)],
        "departments": [{"department_id": d["department_id"], "name": d["name"]} for d in extract_department_names(text, department_list)],
        "medicines": [{"medicine_id": m["medicine_id"], "name": m["name"]} for m in extract_medicine_names(text, medicine_list)],
    }
