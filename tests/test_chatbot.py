"""
MediAssist AI - Chatbot Test Suite
===================================
20+ end-to-end test cases exercising the Orchestrator Agent and every
specialized agent, run against a real (test) Flask app + SQLite DB.

Run with:
    python -m pytest tests/test_chatbot.py -v
or:
    python tests/test_chatbot.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app


class MediAssistChatbotTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        # Log in as the seeded demo patient so patient/appointment/billing
        # intents (which require auth) can also be exercised.
        cls.client.post("/login", data={"username": "john_doe", "password": "Passw0rd!"})

    def chat(self, message):
        resp = self.client.post("/api/chat", json={"message": message})
        self.assertEqual(resp.status_code, 200)
        return resp.get_json()

    # ------------------------------------------------------------------
    # Small talk
    # ------------------------------------------------------------------
    def test_01_greeting(self):
        r = self.chat("Hello")
        self.assertEqual(r["agent"], "OrchestratorAgent")
        self.assertIn("mediassist", r["response"].lower())

    def test_02_thanks(self):
        r = self.chat("Thank you so much")
        self.assertEqual(r["intent"], "thanks")
        self.assertEqual(r["sentiment"]["label"], "Positive")

    def test_03_goodbye(self):
        r = self.chat("Bye, see you later")
        self.assertEqual(r["intent"], "goodbye")

    # ------------------------------------------------------------------
    # Doctor Agent
    # ------------------------------------------------------------------
    def test_04_doctor_search_by_symptom(self):
        r = self.chat("I need a heart doctor")
        self.assertEqual(r["agent"], "DoctorAgent")
        self.assertIn("cardiology", r["response"].lower())

    def test_05_doctor_search_by_department(self):
        r = self.chat("List doctors in orthopedics")
        self.assertEqual(r["agent"], "DoctorAgent")

    def test_06_doctor_availability(self):
        r = self.chat("When is Dr. Arun available?")
        self.assertEqual(r["agent"], "DoctorAgent")
        self.assertIn("Dr. Arun Kumar", [d["full_name"] for d in r["entities"]["doctors"]])

    # ------------------------------------------------------------------
    # Appointment Agent (multi-turn context test - the flagship example)
    # ------------------------------------------------------------------
    def test_07_context_carries_doctor_reference(self):
        r1 = self.chat("I need a heart doctor.")
        self.assertEqual(r1["agent"], "DoctorAgent")
        self.assertIn("Arun", r1["response"])

        r2 = self.chat("Book Arun tomorrow.")
        self.assertEqual(r2["agent"], "AppointmentAgent")
        self.assertIn("confirmed", r2["response"].lower())
        self.assertTrue(any(d["full_name"] == "Dr. Arun Kumar" for d in r2["entities"]["doctors"]))

    def test_08_appointment_book_direct(self):
        r = self.chat("Book an appointment with Dr. Priya Sharma next monday")
        self.assertEqual(r["agent"], "AppointmentAgent")

    def test_09_appointment_check(self):
        r = self.chat("Show my appointments")
        self.assertEqual(r["agent"], "AppointmentAgent")

    def test_10_appointment_partial_slot_filling(self):
        r1 = self.chat("Book Dr. Suresh Reddy")
        self.assertEqual(r1["agent"], "AppointmentAgent")
        self.assertIn("date", r1["response"].lower())

        r2 = self.chat("tomorrow")
        self.assertEqual(r2["agent"], "AppointmentAgent")

    # ------------------------------------------------------------------
    # Department Agent
    # ------------------------------------------------------------------
    def test_11_department_info(self):
        r = self.chat("Tell me about the cardiology department")
        self.assertEqual(r["agent"], "DepartmentAgent")
        self.assertIn("cardiology", r["response"].lower())

    def test_12_department_list(self):
        r = self.chat("List all departments")
        self.assertEqual(r["agent"], "DepartmentAgent")

    # ------------------------------------------------------------------
    # Lab Agent
    # ------------------------------------------------------------------
    def test_13_lab_test_price(self):
        r = self.chat("How much does an MRI cost?")
        self.assertEqual(r["agent"], "LabAgent")

    def test_14_lab_report_status(self):
        r = self.chat("Is my lab report ready?")
        self.assertEqual(r["agent"], "LabAgent")
        self.assertFalse(r.get("requires_login"))

    # ------------------------------------------------------------------
    # Pharmacy Agent
    # ------------------------------------------------------------------
    def test_15_pharmacy_medicine_search(self):
        r = self.chat("Do you have paracetamol available?")
        self.assertEqual(r["agent"], "PharmacyAgent")
        self.assertIn("paracetamol", r["response"].lower())

    def test_16_pharmacy_info(self):
        r = self.chat("What are pharmacy timings?")
        self.assertEqual(r["agent"], "PharmacyAgent")

    # ------------------------------------------------------------------
    # Patient Agent
    # ------------------------------------------------------------------
    def test_17_patient_prescriptions(self):
        r = self.chat("Show my prescriptions")
        self.assertEqual(r["agent"], "PatientAgent")

    def test_18_patient_reports(self):
        r = self.chat("Give me access to my medical reports")
        self.assertEqual(r["agent"], "PatientAgent")

    # ------------------------------------------------------------------
    # Billing Agent
    # ------------------------------------------------------------------
    def test_19_billing_inquiry(self):
        r = self.chat("Show my bills")
        self.assertEqual(r["agent"], "BillingAgent")

    def test_20_insurance_inquiry(self):
        r = self.chat("Do you accept my insurance?")
        self.assertEqual(r["agent"], "BillingAgent")

    # ------------------------------------------------------------------
    # Triage Agent
    # ------------------------------------------------------------------
    def test_21_triage_symptom_routing(self):
        r = self.chat("I have a headache and mild fever")
        self.assertEqual(r["agent"], "TriageAgent")
        self.assertIn("not able to diagnose", r["response"].lower())

    def test_22_triage_knee_pain(self):
        r = self.chat("My knee has been hurting for two days")
        self.assertEqual(r["agent"], "TriageAgent")

    # ------------------------------------------------------------------
    # Emergency Agent (safety-critical - must always win)
    # ------------------------------------------------------------------
    def test_23_emergency_chest_pain(self):
        r = self.chat("I am having severe chest pain and can't breathe")
        self.assertEqual(r["agent"], "EmergencyAgent")
        self.assertTrue(r["is_emergency"])
        self.assertIn("emergency", r["response"].lower())

    def test_24_emergency_unconscious(self):
        r = self.chat("My father just collapsed and is unconscious")
        self.assertEqual(r["agent"], "EmergencyAgent")
        self.assertTrue(r["is_emergency"])

    def test_25_emergency_overrides_pending_context(self):
        # Even mid-booking flow, an emergency message must be caught immediately.
        self.chat("Book Dr. Arun")  # sets pending_action awaiting date
        r = self.chat("Never mind - there is severe bleeding, please help!")
        self.assertEqual(r["agent"], "EmergencyAgent")
        self.assertTrue(r["is_emergency"])

    # ------------------------------------------------------------------
    # FAQ Agent
    # ------------------------------------------------------------------
    def test_26_faq_visiting_hours(self):
        r = self.chat("What are the visiting hours?")
        self.assertEqual(r["agent"], "FAQAgent")

    def test_27_faq_parking(self):
        r = self.chat("Is parking available?")
        self.assertEqual(r["agent"], "FAQAgent")

    # ------------------------------------------------------------------
    # NLP feature sanity checks (via the debug payload)
    # ------------------------------------------------------------------
    def test_28_nlp_pipeline_present(self):
        r = self.chat("I have severe joint pain in my knee")
        self.assertIn("tokens", r["nlp_pipeline"])
        self.assertIn("stemmed_tokens", r["nlp_pipeline"])
        self.assertIn("lemmatized_tokens", r["nlp_pipeline"])
        self.assertIn("pos_tags", r["nlp_pipeline"])
        self.assertGreater(len(r["nlp_pipeline"]["tokens"]), 0)

    def test_29_sentiment_negative_detected(self):
        r = self.chat("This pain is terrible and I am so worried")
        self.assertIn(r["sentiment"]["label"], ("Negative", "Distressed"))

    def test_30_confidence_is_reasonable(self):
        r = self.chat("I need a heart doctor")
        self.assertGreater(r["confidence"], 30)

    # ------------------------------------------------------------------
    # Emergency Detection (expanded keyword coverage)
    # ------------------------------------------------------------------
    def test_31_emergency_accident_bleeding(self):
        r = self.chat("there was a road accident and he is bleeding heavily")
        self.assertEqual(r["agent"], "EmergencyAgent")
        self.assertTrue(r["is_emergency"])

    def test_32_emergency_breathing_difficulty(self):
        r = self.chat("I am having breathing difficulty since morning")
        self.assertEqual(r["agent"], "EmergencyAgent")
        self.assertTrue(r["is_emergency"])

    # ------------------------------------------------------------------
    # Patient Medical History (combined timeline)
    # ------------------------------------------------------------------
    def test_33_medical_history_via_chatbot(self):
        r = self.chat("show my medical history")
        self.assertEqual(r["agent"], "PatientAgent")
        self.assertIn("medical history", r["response"].lower())

    def test_34_medical_history_alt_phrasing(self):
        r = self.chat("what happened in my past visits")
        self.assertEqual(r["agent"], "PatientAgent")

    def test_35_medical_history_page_renders(self):
        resp = self.client.get("/medical-history")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Timeline", resp.data)

    # ------------------------------------------------------------------
    # Billing History (category breakdown + payment history)
    # ------------------------------------------------------------------
    def test_36_billing_history_via_chatbot(self):
        r = self.chat("show my billing history")
        self.assertEqual(r["agent"], "BillingAgent")
        self.assertIn("consultation fees", r["response"].lower())

    def test_37_billing_history_paid_so_far(self):
        r = self.chat("how much have I paid so far")
        self.assertEqual(r["agent"], "BillingAgent")

    def test_38_bills_page_shows_breakdown_and_payments(self):
        resp = self.client.get("/bills")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Payment History", resp.data)
        self.assertIn(b"Charges Breakdown", resp.data)

    def test_39_emergency_page_renders(self):
        resp = self.client.get("/emergency")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Emergency Care", resp.data)
        self.assertIn(b"Emergency Helpline", resp.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
