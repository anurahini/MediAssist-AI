"""
Seeds the MediAssist AI database with realistic sample data:
departments, doctors, patients/users, medicines, lab tests, FAQs,
hospital services, and a few sample appointments/bills/prescriptions/
lab reports so every dashboard page has content to show out of the box.

Run directly:  python database/seed_data.py
"""
import os
import sys
import sqlite3
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_connection, init_db, DB_PATH
from werkzeug.security import generate_password_hash


def already_seeded(conn):
    row = conn.execute("SELECT COUNT(*) as c FROM departments").fetchone()
    return row["c"] > 0


def seed():
    # Fresh DB each time this script is run directly
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # -----------------------------------------------------------------
    # DEPARTMENTS
    # -----------------------------------------------------------------
    departments = [
        ("Cardiology", "Heart and cardiovascular care", "ECG, Angiography, Bypass Surgery, Cardiac Rehab", "Block A, 2nd Floor", "Mon-Sat 9:00 AM - 5:00 PM", "201"),
        ("Neurology", "Brain, spine and nervous system care", "EEG, Stroke Care, Migraine Clinic, Epilepsy Treatment", "Block A, 3rd Floor", "Mon-Sat 9:00 AM - 5:00 PM", "301"),
        ("Orthopedics", "Bones, joints and muscle care", "Joint Replacement, Fracture Care, Physiotherapy, Sports Injury", "Block B, 1st Floor", "Mon-Sat 8:00 AM - 6:00 PM", "101"),
        ("Pediatrics", "Child healthcare from birth to adolescence", "Vaccination, Growth Monitoring, Newborn Care", "Block C, Ground Floor", "Mon-Sun 8:00 AM - 8:00 PM", "001"),
        ("Dermatology", "Skin, hair and nail care", "Acne Treatment, Skin Allergy, Cosmetic Dermatology", "Block B, 2nd Floor", "Mon-Sat 10:00 AM - 4:00 PM", "202"),
        ("General Medicine", "Primary and general adult healthcare", "Fever Clinic, Diabetes Care, Health Checkups", "Block A, Ground Floor", "Mon-Sun 8:00 AM - 8:00 PM", "002"),
        ("ENT", "Ear, nose and throat care", "Hearing Tests, Sinus Treatment, Tonsillectomy", "Block B, 3rd Floor", "Mon-Sat 9:00 AM - 5:00 PM", "302"),
        ("Gynecology", "Women's health and maternity care", "Prenatal Care, Delivery, Infertility Treatment", "Block C, 1st Floor", "Mon-Sat 9:00 AM - 6:00 PM", "102"),
        ("Ophthalmology", "Eye care and vision correction", "Cataract Surgery, LASIK, Eye Checkups", "Block B, Ground Floor", "Mon-Sat 9:00 AM - 5:00 PM", "003"),
        ("Emergency Medicine", "24x7 emergency and trauma care", "Trauma Care, Ambulance, ICU, Critical Care", "Ground Floor, Main Entrance", "24 Hours / 7 Days", "000"),
        ("Psychiatry", "Mental health and counseling", "Counseling, Therapy, Stress Management", "Block C, 2nd Floor", "Mon-Sat 10:00 AM - 5:00 PM", "203"),
        ("Urology", "Kidney and urinary tract care", "Kidney Stone Treatment, Prostate Care", "Block A, 4th Floor", "Mon-Sat 9:00 AM - 4:00 PM", "401"),
    ]
    cur.executemany(
        "INSERT INTO departments (name, description, services, location, timings, contact_ext) VALUES (?,?,?,?,?,?)",
        departments,
    )

    dept_ids = {row["name"]: row["department_id"] for row in cur.execute("SELECT department_id, name FROM departments").fetchall()}

    # -----------------------------------------------------------------
    # DOCTORS
    # -----------------------------------------------------------------
    doctors = [
        ("Dr. Arun Kumar", "Cardiology", "Interventional Cardiologist", "MD, DM Cardiology", 15, "Mon,Tue,Wed,Thu,Fri", "09:00-13:00", 800, 4.8, "A-201"),
        ("Dr. Priya Sharma", "Cardiology", "Cardiac Surgeon", "MS, MCh CTVS", 12, "Mon,Wed,Fri,Sat", "14:00-18:00", 900, 4.7, "A-202"),
        ("Dr. Rajesh Nair", "Neurology", "Neurologist", "MD, DM Neurology", 18, "Mon,Tue,Thu,Fri", "09:00-13:00", 850, 4.9, "A-301"),
        ("Dr. Kavya Menon", "Neurology", "Pediatric Neurologist", "MD, DM Neurology", 9, "Tue,Wed,Thu,Sat", "10:00-14:00", 750, 4.6, "A-302"),
        ("Dr. Suresh Reddy", "Orthopedics", "Orthopedic Surgeon", "MS Ortho", 20, "Mon,Tue,Wed,Fri,Sat", "08:00-12:00", 700, 4.7, "B-101"),
        ("Dr. Anjali Iyer", "Orthopedics", "Joint Replacement Specialist", "MS Ortho, Fellowship Joint Replacement", 11, "Mon,Wed,Thu,Sat", "13:00-17:00", 750, 4.5, "B-102"),
        ("Dr. Meera Pillai", "Pediatrics", "Pediatrician", "MD Pediatrics", 14, "Mon,Tue,Wed,Thu,Fri,Sat", "09:00-13:00", 500, 4.9, "C-001"),
        ("Dr. Karthik Raman", "Pediatrics", "Neonatologist", "MD Pediatrics, Fellowship Neonatology", 8, "Mon,Tue,Thu,Fri", "14:00-18:00", 600, 4.6, "C-002"),
        ("Dr. Divya Nambiar", "Dermatology", "Dermatologist", "MD Dermatology", 10, "Mon,Wed,Fri,Sat", "10:00-14:00", 600, 4.6, "B-201"),
        ("Dr. Vikram Singh", "General Medicine", "General Physician", "MD General Medicine", 16, "Mon,Tue,Wed,Thu,Fri,Sat", "08:00-12:00", 400, 4.7, "A-001"),
        ("Dr. Neha Gupta", "General Medicine", "General Physician", "MBBS, MD", 7, "Mon,Tue,Wed,Thu,Fri,Sat,Sun", "16:00-20:00", 400, 4.4, "A-002"),
        ("Dr. Anand Krishnan", "ENT", "ENT Surgeon", "MS ENT", 13, "Mon,Tue,Thu,Fri", "09:00-13:00", 600, 4.5, "B-301"),
        ("Dr. Lakshmi Venkat", "Gynecology", "Gynecologist & Obstetrician", "MD, DGO", 17, "Mon,Tue,Wed,Fri,Sat", "10:00-14:00", 700, 4.8, "C-101"),
        ("Dr. Sanjay Bhat", "Ophthalmology", "Eye Surgeon", "MS Ophthalmology", 12, "Mon,Wed,Thu,Sat", "09:00-13:00", 550, 4.6, "B-001"),
        ("Dr. Ritu Chawla", "Psychiatry", "Psychiatrist", "MD Psychiatry", 9, "Tue,Wed,Thu,Fri", "11:00-15:00", 650, 4.7, "C-201"),
        ("Dr. Manoj Pillai", "Urology", "Urologist", "MS, MCh Urology", 14, "Mon,Tue,Thu,Fri", "09:00-13:00", 700, 4.5, "A-401"),
        ("Dr. Deepak Menon", "Emergency Medicine", "Emergency Physician", "MD Emergency Medicine", 10, "Mon,Tue,Wed,Thu,Fri,Sat,Sun", "00:00-23:59", 500, 4.8, "ER-1"),
    ]
    for name, dept, spec, qual, exp, days, time_, fee, rating, room in doctors:
        cur.execute(
            "INSERT INTO doctors (full_name, department_id, specialization, qualification, experience_years, available_days, available_time, consultation_fee, rating, room_no) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (name, dept_ids[dept], spec, qual, exp, days, time_, fee, rating, room),
        )

    # -----------------------------------------------------------------
    # USERS  (1 admin + 3 demo patients).  All demo passwords: Passw0rd!
    # -----------------------------------------------------------------
    pw = generate_password_hash("Passw0rd!")
    users = [
        ("admin", "admin@mediassist.ai", pw, "admin", "Hospital Admin", "9999900000"),
        ("john_doe", "john@example.com", pw, "patient", "John Doe", "9876543210"),
        ("sara_p", "sara@example.com", pw, "patient", "Sara Peterson", "9876500000"),
        ("ravi_k", "ravi@example.com", pw, "patient", "Ravi Kumar", "9123456780"),
    ]
    cur.executemany(
        "INSERT INTO users (username, email, password_hash, role, full_name, phone) VALUES (?,?,?,?,?,?)",
        users,
    )
    user_ids = {row["username"]: row["user_id"] for row in cur.execute("SELECT user_id, username FROM users").fetchall()}

    patients = [
        (user_ids["john_doe"], "1990-05-14", "Male", "O+", "12 Park Street, Springfield", "9876500001"),
        (user_ids["sara_p"], "1995-11-02", "Female", "A+", "45 Lake View Road, Springfield", "9876500002"),
        (user_ids["ravi_k"], "1988-02-20", "Male", "B+", "78 MG Road, Springfield", "9876500003"),
    ]
    cur.executemany(
        "INSERT INTO patients (user_id, date_of_birth, gender, blood_group, address, emergency_contact) VALUES (?,?,?,?,?,?)",
        patients,
    )
    patient_ids = {row["user_id"]: row["patient_id"] for row in cur.execute("SELECT patient_id, user_id FROM patients").fetchall()}
    john_pid = patient_ids[user_ids["john_doe"]]
    sara_pid = patient_ids[user_ids["sara_p"]]
    ravi_pid = patient_ids[user_ids["ravi_k"]]

    doctor_ids = {row["full_name"]: row["doctor_id"] for row in cur.execute("SELECT doctor_id, full_name FROM doctors").fetchall()}

    # -----------------------------------------------------------------
    # MEDICINES
    # -----------------------------------------------------------------
    medicines = [
        ("Paracetamol 500mg", "Analgesic/Antipyretic", 20.0, 500, 0, "Cipla", "Used for fever and mild pain relief"),
        ("Amoxicillin 500mg", "Antibiotic", 85.0, 200, 1, "Sun Pharma", "Broad spectrum antibiotic"),
        ("Cetirizine 10mg", "Antihistamine", 15.0, 300, 0, "Zydus", "Relieves allergy symptoms"),
        ("Metformin 500mg", "Antidiabetic", 45.0, 250, 1, "Dr. Reddy's", "Controls blood sugar in type 2 diabetes"),
        ("Atorvastatin 10mg", "Statin", 90.0, 150, 1, "Lupin", "Lowers cholesterol"),
        ("Omeprazole 20mg", "Antacid/PPI", 60.0, 220, 0, "Cipla", "Reduces stomach acid"),
        ("Amlodipine 5mg", "Antihypertensive", 55.0, 180, 1, "Sun Pharma", "Controls high blood pressure"),
        ("Azithromycin 250mg", "Antibiotic", 120.0, 100, 1, "Alkem", "Treats bacterial infections"),
        ("Ibuprofen 400mg", "NSAID", 25.0, 400, 0, "Cipla", "Pain and inflammation relief"),
        ("Cough Syrup (Ascoril)", "Cough & Cold", 95.0, 90, 0, "Glenmark", "Relieves cough and congestion"),
        ("Vitamin D3 60000 IU", "Supplement", 30.0, 300, 0, "Mankind", "Vitamin D supplementation"),
        ("Insulin Glargine", "Antidiabetic (injectable)", 650.0, 60, 1, "Sanofi", "Long-acting insulin for diabetes"),
        ("ORS Sachets", "Rehydration", 10.0, 600, 0, "GSK", "Oral rehydration salts"),
        ("Multivitamin Tablets", "Supplement", 150.0, 250, 0, "Himalaya", "Daily multivitamin support"),
        ("Losartan 50mg", "Antihypertensive", 65.0, 140, 1, "Cipla", "Manages high blood pressure"),
    ]
    cur.executemany(
        "INSERT INTO medicines (name, category, price, stock_quantity, requires_prescription, manufacturer, description) VALUES (?,?,?,?,?,?,?)",
        medicines,
    )

    # -----------------------------------------------------------------
    # LAB TESTS
    # -----------------------------------------------------------------
    lab_tests = [
        ("Complete Blood Count (CBC)", "Blood Test", 350, "No special preparation needed", "6 hours"),
        ("Blood Sugar (Fasting)", "Blood Test", 150, "8-10 hours fasting required", "3 hours"),
        ("Lipid Profile", "Blood Test", 500, "10-12 hours fasting required", "12 hours"),
        ("Thyroid Profile (T3 T4 TSH)", "Blood Test", 600, "No fasting required, morning sample preferred", "24 hours"),
        ("Liver Function Test (LFT)", "Blood Test", 550, "8 hours fasting recommended", "12 hours"),
        ("Kidney Function Test (KFT)", "Blood Test", 500, "No special preparation", "12 hours"),
        ("ECG", "Cardiac Test", 250, "Avoid caffeine 2 hours before test", "1 hour"),
        ("2D Echo", "Cardiac Test", 1800, "No special preparation", "Same day"),
        ("X-Ray Chest", "Imaging", 400, "Remove metallic objects before scan", "2 hours"),
        ("MRI Brain", "Imaging", 6500, "Remove all metal objects, inform if claustrophobic", "24 hours"),
        ("CT Scan Abdomen", "Imaging", 4500, "4-6 hours fasting may be required", "24 hours"),
        ("Urine Routine Examination", "Urine Test", 150, "Collect midstream morning sample", "4 hours"),
        ("HbA1c", "Blood Test", 450, "No fasting required", "24 hours"),
        ("Vitamin D Test", "Blood Test", 900, "No special preparation", "48 hours"),
        ("COVID-19 RT-PCR", "Infectious Disease", 500, "No preparation, avoid eating 30 mins before swab", "24 hours"),
    ]
    cur.executemany(
        "INSERT INTO lab_tests (test_name, category, price, preparation, report_time) VALUES (?,?,?,?,?)",
        lab_tests,
    )
    test_ids = {row["test_name"]: row["test_id"] for row in cur.execute("SELECT test_id, test_name FROM lab_tests").fetchall()}

    # -----------------------------------------------------------------
    # FAQS
    # -----------------------------------------------------------------
    faqs = [
        ("What are the hospital visiting hours?", "General visiting hours are 11:00 AM - 1:00 PM and 5:00 PM - 7:00 PM daily. ICU visiting is restricted to 2 visitors at a time.", "timings"),
        ("What are the OPD timings?", "Our OPD is open Monday to Saturday from 8:00 AM to 8:00 PM, and Sunday from 9:00 AM to 1:00 PM for select departments.", "timings"),
        ("Is parking available at the hospital?", "Yes, we have a multi-level parking facility with space for 300+ vehicles. Parking is free for the first 2 hours and chargeable afterwards.", "facilities"),
        ("Do you have a pharmacy inside the hospital?", "Yes, our 24x7 in-house pharmacy is located on the Ground Floor near the main entrance.", "facilities"),
        ("Is there a cafeteria in the hospital?", "Yes, the hospital cafeteria on the 1st floor of Block C is open from 7:00 AM to 10:00 PM daily.", "facilities"),
        ("How can I contact the hospital?", "You can reach us at +91-1800-123-4567 (toll free) or email us at contact@mediassist-hospital.com.", "contact"),
        ("Do you accept health insurance?", "Yes, we accept most major health insurance providers including cashless treatment for empanelled insurers. Please check with our billing desk for your specific provider.", "billing"),
        ("Is ambulance service available?", "Yes, we provide 24x7 ambulance service. Call our emergency helpline +91-1800-123-9999 for immediate assistance.", "emergency"),
        ("Where is the hospital located?", "MediAssist Hospital is located at 100 Wellness Avenue, Springfield. We are easily accessible by public transport and have dedicated parking.", "general"),
        ("Do I need to bring anything for my appointment?", "Please carry a valid ID proof, any previous medical records/reports, and your insurance card if applicable.", "appointments"),
        ("Can I get a duplicate bill or report?", "Yes, duplicate bills and reports can be requested from the billing/records desk or downloaded from your patient dashboard.", "billing"),
        ("What safety measures are followed at the hospital?", "We follow strict infection control protocols, regular sanitization, and have dedicated isolation wards for infectious cases.", "general"),
        ("Do you provide online consultations?", "Yes, teleconsultation is available for select departments. Please book through the appointment section and select 'Online Consultation'.", "appointments"),
        ("What is the process for emergency admission?", "Walk directly into our 24x7 Emergency Department at the main entrance, or call our ambulance helpline for pickup. No prior appointment is needed for emergencies.", "emergency"),
        ("Are wheelchairs available at the hospital?", "Yes, wheelchairs are available free of charge at all entrances. Please ask our helpdesk staff for assistance.", "facilities"),
    ]
    cur.executemany("INSERT INTO faqs (question, answer, category) VALUES (?,?,?)", faqs)

    # -----------------------------------------------------------------
    # HOSPITAL SERVICES
    # -----------------------------------------------------------------
    services = [
        ("24x7 Emergency Care", "Round the clock emergency and trauma care with dedicated ambulance fleet.", "24 Hours"),
        ("ICU & Critical Care", "State of the art intensive care units with advanced life support.", "24 Hours"),
        ("In-house Pharmacy", "Fully stocked pharmacy for prescription and over-the-counter medicines.", "24 Hours"),
        ("Diagnostic Lab", "NABL accredited laboratory for all pathology and radiology tests.", "6:00 AM - 10:00 PM"),
        ("Blood Bank", "Licensed blood bank with all blood groups and components available.", "24 Hours"),
        ("Ambulance Service", "GPS enabled ambulances with paramedic staff for emergency transport.", "24 Hours"),
        ("Health Checkup Packages", "Comprehensive preventive health checkup packages for all age groups.", "8:00 AM - 4:00 PM"),
        ("Physiotherapy Center", "Advanced physiotherapy and rehabilitation services.", "9:00 AM - 6:00 PM"),
    ]
    cur.executemany("INSERT INTO hospital_services (name, description, availability) VALUES (?,?,?)", services)

    # -----------------------------------------------------------------
    # SAMPLE APPOINTMENTS, PRESCRIPTIONS, LAB REPORTS, BILLS & PAYMENTS
    # A richer, multi-visit history per patient so the Medical History
    # timeline and Billing History breakdown have real data to show.
    # -----------------------------------------------------------------
    today = date.today()
    d1 = (today + timedelta(days=2)).isoformat()          # upcoming
    d2 = (today - timedelta(days=5)).isoformat()           # recent past
    d3 = (today + timedelta(days=7)).isoformat()           # upcoming
    d_1m = (today - timedelta(days=32)).isoformat()        # ~1 month ago
    d_2m = (today - timedelta(days=63)).isoformat()        # ~2 months ago
    d_3m = (today - timedelta(days=95)).isoformat()        # ~3 months ago

    # ---- John Doe: richest history (main demo patient) ----
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Arun Kumar"], d1, "09:30", "confirmed", "Chest discomfort follow-up"),
    )
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Vikram Singh"], d2, "08:30", "completed", "Fever and body ache"),
    )
    appt2 = cur.lastrowid
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Arun Kumar"], d_1m, "10:00", "completed", "Occasional chest pain and palpitations"),
    )
    appt3 = cur.lastrowid
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Vikram Singh"], d_2m, "09:00", "completed", "Annual health checkup"),
    )
    appt4 = cur.lastrowid

    # ---- Sara Peterson ----
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (sara_pid, doctor_ids["Dr. Lakshmi Venkat"], d3, "10:00", "confirmed", "Routine prenatal checkup"),
    )
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (sara_pid, doctor_ids["Dr. Lakshmi Venkat"], d_1m, "10:30", "completed", "First prenatal consultation"),
    )
    sara_appt1 = cur.lastrowid

    # ---- Ravi Kumar ----
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (ravi_pid, doctor_ids["Dr. Suresh Reddy"], d2, "08:00", "completed", "Knee pain"),
    )
    ravi_appt1 = cur.lastrowid
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, appointment_time, status, reason) VALUES (?,?,?,?,?,?)",
        (ravi_pid, doctor_ids["Dr. Suresh Reddy"], d_3m, "08:30", "completed", "Lower back pain after a fall"),
    )
    ravi_appt2 = cur.lastrowid

    # ---- PRESCRIPTIONS ----
    cur.execute(
        "INSERT INTO prescriptions (patient_id, doctor_id, appointment_id, medicines, notes, date_issued) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Vikram Singh"], appt2, "Paracetamol 500mg:1 tab twice daily for 3 days, ORS Sachets:1 sachet daily", "Rest and stay hydrated. Follow up if fever persists beyond 3 days.", d2),
    )
    cur.execute(
        "INSERT INTO prescriptions (patient_id, doctor_id, appointment_id, medicines, notes, date_issued) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Arun Kumar"], appt3, "Amlodipine 5mg:1 tab daily, Atorvastatin 10mg:1 tab at night", "Monitor blood pressure daily. Reduce salt intake. Follow up in 4 weeks.", d_1m),
    )
    cur.execute(
        "INSERT INTO prescriptions (patient_id, doctor_id, appointment_id, medicines, notes, date_issued) VALUES (?,?,?,?,?,?)",
        (john_pid, doctor_ids["Dr. Vikram Singh"], appt4, "Multivitamin Tablets:1 tab daily, Vitamin D3 60000 IU:1 sachet weekly", "Overall health good. Continue supplements for 8 weeks.", d_2m),
    )
    cur.execute(
        "INSERT INTO prescriptions (patient_id, doctor_id, appointment_id, medicines, notes, date_issued) VALUES (?,?,?,?,?,?)",
        (ravi_pid, doctor_ids["Dr. Suresh Reddy"], ravi_appt2, "Ibuprofen 400mg:1 tab twice daily for 5 days", "Avoid heavy lifting for 2 weeks. Apply hot compress for relief.", d_3m),
    )

    # ---- LAB REPORTS ----
    cur.execute(
        "INSERT INTO lab_reports (patient_id, test_id, booked_date, status, result_summary, report_file) VALUES (?,?,?,?,?,?)",
        (john_pid, test_ids["Complete Blood Count (CBC)"], d2, "ready", "All parameters within normal range.", "CBC_John_Doe.pdf"),
    )
    cur.execute(
        "INSERT INTO lab_reports (patient_id, test_id, booked_date, status, result_summary, report_file) VALUES (?,?,?,?,?,?)",
        (john_pid, test_ids["ECG"], d1, "pending", None, None),
    )
    cur.execute(
        "INSERT INTO lab_reports (patient_id, test_id, booked_date, status, result_summary, report_file) VALUES (?,?,?,?,?,?)",
        (john_pid, test_ids["Lipid Profile"], d_1m, "ready", "Slightly elevated LDL cholesterol. Dietary changes recommended.", "Lipid_John_Doe.pdf"),
    )
    cur.execute(
        "INSERT INTO lab_reports (patient_id, test_id, booked_date, status, result_summary, report_file) VALUES (?,?,?,?,?,?)",
        (john_pid, test_ids["Thyroid Profile (T3 T4 TSH)"], d_2m, "ready", "Thyroid levels within normal range.", "Thyroid_John_Doe.pdf"),
    )
    cur.execute(
        "INSERT INTO lab_reports (patient_id, test_id, booked_date, status, result_summary, report_file) VALUES (?,?,?,?,?,?)",
        (ravi_pid, test_ids["X-Ray Chest"], d2, "ready", "No abnormality detected.", "XRay_Ravi_Kumar.pdf"),
    )

    # ---- BILLS (categorized: consultation / lab / pharmacy / other) ----
    def add_bill(patient_id, description, amount, status, category, insured, provider, issued, due):
        cur.execute(
            "INSERT INTO bills (patient_id, description, amount, status, category, insurance_covered, "
            "insurance_provider, date_issued, due_date) VALUES (?,?,?,?,?,?,?,?,?)",
            (patient_id, description, amount, status, category, 1 if insured else 0, provider, issued, due),
        )
        return cur.lastrowid

    def add_payment(bill_id, patient_id, amount, method, paid_at):
        cur.execute(
            "INSERT INTO payments (bill_id, patient_id, amount_paid, payment_method, paid_at) VALUES (?,?,?,?,?)",
            (bill_id, patient_id, amount, method, paid_at),
        )

    # John Doe billing history
    b = add_bill(john_pid, "Consultation - Dr. Vikram Singh + CBC Test", 750, "paid", "consultation", False, None, d2, d2)
    add_payment(b, john_pid, 750, "UPI", d2 + " 14:20:00")
    b = add_bill(john_pid, "Cardiology Consultation - Dr. Arun Kumar", 800, "unpaid", "consultation", True, "Star Health Insurance", today.isoformat(), (today + timedelta(days=15)).isoformat())
    b = add_bill(john_pid, "Cardiology Follow-up + Lipid Profile Test", 1300, "paid", "consultation", False, None, d_1m, d_1m)
    add_payment(b, john_pid, 1300, "Card", d_1m + " 11:05:00")
    b = add_bill(john_pid, "Lipid Profile Test", 500, "paid", "lab", False, None, d_1m, d_1m)
    add_payment(b, john_pid, 500, "Card", d_1m + " 11:06:00")
    b = add_bill(john_pid, "Pharmacy - Amlodipine + Atorvastatin (30 days)", 345, "paid", "pharmacy", False, None, d_1m, d_1m)
    add_payment(b, john_pid, 345, "Cash", d_1m + " 11:30:00")
    b = add_bill(john_pid, "Annual Health Checkup - Dr. Vikram Singh", 400, "paid", "consultation", False, None, d_2m, d_2m)
    add_payment(b, john_pid, 400, "UPI", d_2m + " 09:45:00")
    b = add_bill(john_pid, "Thyroid Profile Test", 600, "paid", "lab", False, None, d_2m, d_2m)
    add_payment(b, john_pid, 600, "UPI", d_2m + " 09:50:00")

    # Sara Peterson billing history
    b = add_bill(sara_pid, "Prenatal Consultation - Dr. Lakshmi Venkat", 700, "paid", "consultation", False, None, d_1m, d_1m)
    add_payment(b, sara_pid, 700, "Card", d_1m + " 12:00:00")
    b = add_bill(sara_pid, "Pharmacy - Multivitamin Tablets", 150, "paid", "pharmacy", False, None, d_1m, d_1m)
    add_payment(b, sara_pid, 150, "Cash", d_1m + " 12:15:00")

    # Ravi Kumar billing history
    b = add_bill(ravi_pid, "Orthopedic Consultation + X-Ray", 1100, "paid", "consultation", False, None, d2, d2)
    add_payment(b, ravi_pid, 1100, "Card", d2 + " 10:00:00")
    b = add_bill(ravi_pid, "Orthopedic Consultation - Back Pain", 700, "paid", "consultation", False, None, d_3m, d_3m)
    add_payment(b, ravi_pid, 700, "UPI", d_3m + " 09:15:00")
    b = add_bill(ravi_pid, "Pharmacy - Ibuprofen 400mg", 125, "unpaid", "pharmacy", False, None, d_3m, (today + timedelta(days=5)).isoformat())

    conn.commit()
    conn.close()
    print("Database seeded successfully at:", DB_PATH)


if __name__ == "__main__":
    seed()
