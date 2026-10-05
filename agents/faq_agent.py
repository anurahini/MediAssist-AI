"""
FAQ Agent
---------
Answers general hospital questions (timings, parking, facilities,
visiting hours, contact info) using TF-IDF similarity search over the
faqs table so it can match paraphrased questions, not just exact
matches.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database.db import query

_vectorizer = None
_faq_vectors = None
_faq_cache = None


def _build_index():
    global _vectorizer, _faq_vectors, _faq_cache
    _faq_cache = query("SELECT * FROM faqs")
    corpus = [f["question"] for f in _faq_cache]
    _vectorizer = TfidfVectorizer(ngram_range=(1, 2))
    _faq_vectors = _vectorizer.fit_transform(corpus)


def handle(text: str, entities: dict, sentiment: dict, session_id: str, user=None) -> dict:
    global _vectorizer, _faq_vectors, _faq_cache
    if _vectorizer is None:
        _build_index()

    query_vec = _vectorizer.transform([text])
    sims = cosine_similarity(query_vec, _faq_vectors)[0]
    best_idx = sims.argmax()
    best_score = sims[best_idx]

    if best_score >= 0.15:
        faq = _faq_cache[best_idx]
        return {"text": faq["answer"], "data": {"matched_question": faq["question"], "similarity": round(float(best_score), 2)}}

    # Fallback: show a few general FAQs
    sample = _faq_cache[:5]
    lines = "\n".join(f"- {f['question']}" for f in sample)
    msg = ("I'm not fully sure which hospital info you need — here are some things I can help "
           f"with:\n\n{lines}\n\nFeel free to ask me any of these!")
    return {"text": msg, "data": {}}
