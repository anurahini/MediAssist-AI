"""
MediAssist AI - NLP Pipeline Unit Tests
=========================================
Unit tests for the individual NLP building blocks (independent of
Flask/DB): tokenization, stopword removal, stemming, lemmatization,
POS tagging, NER, sentiment analysis and intent classification.

Run with:
    python -m pytest tests/test_nlp.py -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp import preprocessor, sentiment, ner, intent_classifier


class PreprocessorTests(unittest.TestCase):
    def test_tokenize(self):
        tokens = preprocessor.tokenize("I need a heart doctor!")
        self.assertIn("heart", tokens)
        self.assertIn("doctor", tokens)

    def test_stopword_removal(self):
        tokens = preprocessor.tokenize("I need a doctor for the pain")
        filtered = preprocessor.remove_stopwords(tokens)
        self.assertNotIn("a", filtered)
        self.assertNotIn("the", filtered)
        self.assertIn("doctor", filtered)
        self.assertIn("pain", filtered)

    def test_negation_preserved(self):
        tokens = preprocessor.tokenize("I have no pain")
        filtered = preprocessor.remove_stopwords(tokens)
        self.assertIn("no", filtered)

    def test_stemming(self):
        stemmed = preprocessor.stem_tokens(["running", "doctors", "booking"])
        self.assertEqual(stemmed[0], "run")

    def test_lemmatization(self):
        lemmas = preprocessor.lemmatize_tokens(["doctors", "appointments"])
        self.assertEqual(lemmas[0], "doctor")
        self.assertEqual(lemmas[1], "appointment")

    def test_pos_tags(self):
        tags = preprocessor.pos_tags(["I", "need", "a", "doctor"])
        self.assertEqual(len(tags), 4)

    def test_full_pipeline_keys(self):
        result = preprocessor.full_pipeline("Book Dr. Arun tomorrow")
        for key in ["tokens", "tokens_no_stopwords", "stemmed_tokens", "lemmatized_tokens", "pos_tags"]:
            self.assertIn(key, result)


class SentimentTests(unittest.TestCase):
    def test_positive_sentiment(self):
        result = sentiment.analyze_sentiment("Thank you so much, this is great!")
        self.assertEqual(result["label"], "Positive")

    def test_negative_sentiment(self):
        result = sentiment.analyze_sentiment("This pain is terrible and unbearable")
        self.assertIn(result["label"], ("Negative", "Distressed"))

    def test_neutral_sentiment(self):
        result = sentiment.analyze_sentiment("What are the hospital timings")
        self.assertIn(result["label"], ("Neutral", "Positive"))


class NERTests(unittest.TestCase):
    def test_date_resolution_tomorrow(self):
        dates = ner.extract_dates("book an appointment tomorrow")
        self.assertTrue(any(d["text"] == "tomorrow" and d["resolved_date"] for d in dates))

    def test_symptom_extraction(self):
        symptoms = ner.extract_symptoms("I have a headache and knee pain")
        self.assertIn("headache", symptoms)
        self.assertIn("knee pain", symptoms)

    def test_emergency_signal_detection(self):
        signals = ner.extract_emergency_signals("I am having severe chest pain and can't breathe")
        self.assertTrue(len(signals) > 0)

    def test_doctor_name_matching(self):
        fake_doctors = [{"doctor_id": 1, "full_name": "Dr. Arun Kumar"}]
        matches = ner.extract_doctor_names("book arun tomorrow", fake_doctors)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["full_name"], "Dr. Arun Kumar")


class IntentClassifierTests(unittest.TestCase):
    def test_doctor_search_intent(self):
        result = intent_classifier.predict_intent("I need a heart doctor")
        self.assertEqual(result["intent"], "doctor_search")
        self.assertEqual(result["agent"], "DoctorAgent")

    def test_emergency_intent(self):
        result = intent_classifier.predict_intent("I am having severe chest pain")
        self.assertEqual(result["intent"], "emergency")
        self.assertEqual(result["agent"], "EmergencyAgent")

    def test_faq_intent(self):
        result = intent_classifier.predict_intent("what are the visiting hours")
        self.assertEqual(result["intent"], "faq")

    def test_appointment_book_intent(self):
        result = intent_classifier.predict_intent("book arun tomorrow")
        self.assertEqual(result["intent"], "appointment_book")

    def test_confidence_range(self):
        result = intent_classifier.predict_intent("I need a heart doctor")
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
