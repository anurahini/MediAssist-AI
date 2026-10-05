"""
Text preprocessing utilities for MediAssist AI.
Demonstrates classic NLP pipeline steps using NLTK:
    1. Tokenization
    2. Stopword removal
    3. Stemming (Porter Stemmer)
    4. Lemmatization (WordNet Lemmatizer)
    5. POS tagging

NOTE ON ROBUSTNESS: NLTK needs several data packages downloaded
separately from the library itself (punkt/punkt_tab tokenizer models,
the stopwords corpus, wordnet, and the POS tagger). This project ships
those packages pre-downloaded in the bundled `nltk_data/` folder at the
project root, so the app works fully offline out of the box and never
depends on NLTK's own download servers being reachable (which corporate
firewalls / antivirus / restrictive networks often block, showing
errors like "WinError 10054"). If that bundle is ever missing for some
reason, this module still tries a live download as a second option, and
finally falls back to a simplified pure-Python implementation so the
chatbot keeps working either way instead of crashing.
"""
import os
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer

# Point NLTK at the bundled data folder shipped with this project,
# ahead of everything else it would normally search.
_BUNDLED_NLTK_DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "nltk_data")
if os.path.isdir(_BUNDLED_NLTK_DATA) and _BUNDLED_NLTK_DATA not in nltk.data.path:
    nltk.data.path.insert(0, _BUNDLED_NLTK_DATA)

_stemmer = PorterStemmer()
_lemmatizer = WordNetLemmatizer()


def _try_download(*package_names):
    """Best-effort download of one or more NLTK data packages. Only
    used as a fallback when the bundled nltk_data/ folder doesn't
    already have what's needed. Silently does nothing if already
    present, and never raises if there's no internet access - callers
    fall back gracefully at call time instead."""
    for name in package_names:
        try:
            nltk.download(name, quiet=True)
        except Exception:
            pass


# Only reach out to the network for packages if the bundled folder
# above isn't present at all (e.g. someone deleted it) - keeps a normal
# run fully offline, instant, and immune to networks that block NLTK's
# download servers (a common source of "WinError 10054" style errors).
if not os.path.isdir(_BUNDLED_NLTK_DATA):
    _try_download(
        "stopwords", "punkt_tab", "punkt", "wordnet", "omw-1.4",
        "averaged_perceptron_tagger_eng", "averaged_perceptron_tagger",
    )

try:
    _STOPWORDS = set(stopwords.words("english"))
except LookupError:
    # Small built-in fallback list so the app still runs fully offline.
    _STOPWORDS = {
        "a", "an", "the", "is", "am", "are", "was", "were", "be", "been", "being",
        "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
        "my", "your", "his", "its", "our", "their", "to", "of", "in", "on", "at",
        "for", "with", "about", "as", "by", "and", "or", "but", "if", "so", "do",
        "does", "did", "can", "could", "will", "would", "shall", "should", "may",
        "might", "must", "this", "that", "these", "those", "there", "here",
    }

# Keep negation words - important for medical context ("no pain" != "pain")
_NEGATIONS = {"no", "not", "nor", "never", "n't"}
_STOPWORDS = _STOPWORDS - _NEGATIONS

# Words that matter a lot in a hospital chatbot context; never strip these
_DOMAIN_KEEP = {"dr", "doctor", "today", "tomorrow", "now"}


def _fallback_tokenize(text: str):
    """Regex-based tokenizer used only if NLTK's punkt data can't be
    loaded at all (e.g. no internet access on first run)."""
    return re.findall(r"[A-Za-z0-9']+|[.,!?;:]", text)


def _safe_word_tokenize(text: str):
    try:
        from nltk.tokenize import word_tokenize
        return word_tokenize(text)
    except LookupError:
        return _fallback_tokenize(text)


def _safe_pos_tag(tokens):
    try:
        from nltk.tag import pos_tag
        return pos_tag(tokens)
    except LookupError:
        # Fallback: no tagger data available - mark everything as unknown
        # rather than crashing, so the debug panel still renders.
        return [(t, "UNK") for t in tokens]


def _safe_lemmatize(token: str) -> str:
    try:
        return _lemmatizer.lemmatize(token.lower())
    except LookupError:
        return token.lower()


_CONTRACTIONS = {
    "can't": "cannot", "won't": "will not", "n't": " not",
    "i'm": "i am", "im": "i am", "you're": "you are", "he's": "he is", "she's": "she is",
    "it's": "it is", "we're": "we are", "they're": "they are", "what's": "what is",
    "where's": "where is", "how's": "how is", "who's": "who is", "when's": "when is",
    "there's": "there is", "that's": "that is", "i've": "i have", "you've": "you have",
    "we've": "we have", "i'll": "i will", "you'll": "you will", "he'll": "he will",
    "she'll": "she will", "we'll": "we will", "they'll": "they will", "i'd": "i would",
    "you'd": "you would", "he'd": "he would", "she'd": "she would", "we'd": "we would",
    "gonna": "going to", "wanna": "want to", "gotta": "got to", "pls": "please",
    "plz": "please", "thx": "thanks", "tks": "thanks", "u": "you", "r": "are",
}


def expand_contractions(text: str) -> str:
    """Expand English contractions and informal casual slang."""
    text_lower = text.lower()
    for contraction, expansion in _CONTRACTIONS.items():
        text_lower = re.sub(r"\b" + re.escape(contraction) + r"\b", expansion, text_lower)
    return text_lower


def clean_text(text: str) -> str:
    """Lowercase, expand contractions, and strip unwanted punctuation while preserving useful chars."""
    text = text.strip()
    text = expand_contractions(text)
    text = re.sub(r"[^a-zA-Z0-9\s\.\,\?\!\-\:']", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def tokenize(text: str):
    """Word tokenization using NLTK's Punkt tokenizer (falls back to a
    simple regex tokenizer if the punkt data isn't available)."""
    return _safe_word_tokenize(clean_text(text))


def remove_stopwords(tokens):
    """Remove common English stopwords (negations preserved)."""
    return [t for t in tokens if t.lower() not in _STOPWORDS or t.lower() in _DOMAIN_KEEP]


def stem_tokens(tokens):
    """Porter stemming of a token list."""
    return [_stemmer.stem(t) for t in tokens]


def lemmatize_tokens(tokens):
    """WordNet lemmatization of a token list (default noun POS)."""
    return [_safe_lemmatize(t) for t in tokens]


def pos_tags(tokens):
    """Return list of (token, POS tag) tuples."""
    return _safe_pos_tag(tokens)


def full_pipeline(text: str) -> dict:
    """
    Run the complete preprocessing pipeline and return every intermediate
    step - used to populate the NLP Demo page and the chatbot debug panel.
    """
    raw_tokens = tokenize(text)
    no_stop = remove_stopwords(raw_tokens)
    stemmed = stem_tokens(no_stop)
    lemmatized = lemmatize_tokens(no_stop)
    tags = pos_tags(raw_tokens)

    return {
        "original_text": text,
        "cleaned_text": clean_text(text),
        "tokens": raw_tokens,
        "tokens_no_stopwords": no_stop,
        "stemmed_tokens": stemmed,
        "lemmatized_tokens": lemmatized,
        "pos_tags": [{"word": w, "tag": t} for w, t in tags],
    }


def normalize_for_model(text: str) -> str:
    """
    Lightweight normalization used before feeding text into the TF-IDF
    intent classifier: lowercase + lemmatize + drop stopwords, joined
    back into a single string.
    """
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    lemmas = lemmatize_tokens(tokens)
    return " ".join(lemmas)
