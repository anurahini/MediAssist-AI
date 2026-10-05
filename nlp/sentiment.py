"""
Sentiment analysis for MediAssist AI using NLTK's VADER
(Valence Aware Dictionary and sEntiment Reasoner) - well suited for
short, informal chat messages.
"""
import os
import re
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Point NLTK at the bundled data folder shipped with this project (see
# nlp/preprocessor.py for the full explanation) so VADER's lexicon loads
# from disk instantly instead of needing a network download.
_BUNDLED_NLTK_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nltk_data")
if os.path.isdir(_BUNDLED_NLTK_DATA) and _BUNDLED_NLTK_DATA not in nltk.data.path:
    nltk.data.path.insert(0, _BUNDLED_NLTK_DATA)

try:
    _sia = SentimentIntensityAnalyzer()
except LookupError:
    try:
        nltk.download("vader_lexicon", quiet=True)
        _sia = SentimentIntensityAnalyzer()
    except Exception:
        # No internet access at all on first run - fall back to a tiny
        # keyword-based analyzer below rather than crashing every
        # chat request.
        _sia = None

# A few domain-specific words that VADER doesn't know about, tuned for
# a hospital chatbot context (distress / pain words should read negative,
# reassurance words should read positive).
_DOMAIN_LEXICON = {
    "pain": -1.8, "painful": -1.9, "hurts": -1.8, "hurting": -1.7,
    "worried": -1.6, "scared": -1.9, "afraid": -1.8, "terrible": -2.5,
    "severe": -2.0, "worst": -2.5, "emergency": -2.2, "bleeding": -2.0,
    "unbearable": -2.6, "anxious": -1.6, "thanks": 1.8, "thank": 1.8,
    "great": 2.0, "helpful": 1.8, "relieved": 1.9, "better": 1.2,
}
if _sia is not None:
    _sia.lexicon.update(_DOMAIN_LEXICON)


def _fallback_polarity_scores(text: str) -> dict:
    """Very small keyword-count fallback used only when the VADER
    lexicon truly can't be downloaded (no internet on first run)."""
    words = re.findall(r"[a-z']+", text.lower())
    score = sum(_DOMAIN_LEXICON.get(w, 0) for w in words)
    pos = sum(1 for w in words if _DOMAIN_LEXICON.get(w, 0) > 0)
    neg = sum(1 for w in words if _DOMAIN_LEXICON.get(w, 0) < 0)
    total = max(len(words), 1)
    compound = max(-1.0, min(1.0, score / 5.0))
    return {
        "compound": compound,
        "pos": pos / total,
        "neg": neg / total,
        "neu": max(0.0, 1 - (pos + neg) / total),
    }


def analyze_sentiment(text: str) -> dict:
    """
    Returns compound score plus a friendly label:
        Positive / Neutral / Negative / Distressed
    'Distressed' is a hospital-specific escalation label used when the
    negative sentiment is very strong, so the UI/agents can respond with
    extra empathy.
    """
    scores = _sia.polarity_scores(text) if _sia is not None else _fallback_polarity_scores(text)
    compound = scores["compound"]

    if compound <= -0.6:
        label = "Distressed"
    elif compound < -0.15:
        label = "Negative"
    elif compound < 0.15:
        label = "Neutral"
    else:
        label = "Positive"

    return {
        "label": label,
        "compound": round(compound, 3),
        "positive": round(scores["pos"], 3),
        "neutral": round(scores["neu"], 3),
        "negative": round(scores["neg"], 3),
    }
