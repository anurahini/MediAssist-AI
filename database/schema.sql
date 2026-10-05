-- =====================================================================
-- MediAssist AI - Hospital Assistant Chatbot
-- SQLite Database Schema
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- USERS (authentication table - patients, doctors, admins)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username        TEXT UNIQUE NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'patient',   -- patient | admin
    full_name       TEXT NOT NULL,
    phone           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active       INTEGER DEFAULT 1
);

-- ---------------------------------------------------------------------
-- DEPARTMENTS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS departments (
    department_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT UNIQUE NOT NULL,
    description     TEXT,
    services        TEXT,          -- comma separated services
    location        TEXT,          -- floor / block
    timings         TEXT,          -- opening hours
    contact_ext     TEXT
);

-- ---------------------------------------------------------------------
-- DOCTORS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS doctors (
    doctor_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name       TEXT NOT NULL,
    department_id   INTEGER NOT NULL,
    specialization  TEXT NOT NULL,
    qualification   TEXT,
    experience_years INTEGER,
    available_days  TEXT,          -- e.g. Mon,Tue,Wed,Thu,Fri
    available_time  TEXT,          -- e.g. 09:00-13:00
    consultation_fee REAL DEFAULT 500,
    rating          REAL DEFAULT 4.5,
    room_no         TEXT,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- ---------------------------------------------------------------------
-- PATIENTS (linked 1-1 with users of role 'patient')
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS patients (
    patient_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER UNIQUE NOT NULL,
    date_of_birth   TEXT,
    gender          TEXT,
    blood_group     TEXT,
    address         TEXT,
    emergency_contact TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- ---------------------------------------------------------------------
-- APPOINTMENTS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    doctor_id       INTEGER NOT NULL,
    appointment_date TEXT NOT NULL,   -- YYYY-MM-DD
    appointment_time TEXT NOT NULL,   -- HH:MM
    status          TEXT DEFAULT 'confirmed',  -- confirmed | cancelled | completed | rescheduled
    reason          TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
);

-- ---------------------------------------------------------------------
-- MEDICINES (Pharmacy)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicines (
    medicine_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    category        TEXT,
    price           REAL NOT NULL,
    stock_quantity  INTEGER DEFAULT 0,
    requires_prescription INTEGER DEFAULT 0,
    manufacturer    TEXT,
    description     TEXT
);

-- ---------------------------------------------------------------------
-- PRESCRIPTIONS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS prescriptions (
    prescription_id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    doctor_id       INTEGER NOT NULL,
    appointment_id  INTEGER,
    medicines       TEXT NOT NULL,   -- comma separated "name:dosage"
    notes           TEXT,
    date_issued     TEXT NOT NULL,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
);

-- ---------------------------------------------------------------------
-- LAB TESTS (catalog)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab_tests (
    test_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name       TEXT NOT NULL,
    category        TEXT,
    price           REAL NOT NULL,
    preparation     TEXT,           -- fasting required etc.
    report_time     TEXT            -- e.g. "24 hours"
);

-- ---------------------------------------------------------------------
-- LAB REPORTS (booked/completed tests for a patient)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lab_reports (
    report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    test_id         INTEGER NOT NULL,
    booked_date     TEXT NOT NULL,
    status          TEXT DEFAULT 'pending',   -- pending | processing | ready
    result_summary  TEXT,
    report_file     TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
    FOREIGN KEY (test_id) REFERENCES lab_tests(test_id)
);

-- ---------------------------------------------------------------------
-- BILLS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bills (
    bill_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id      INTEGER NOT NULL,
    description     TEXT NOT NULL,
    amount          REAL NOT NULL,
    status          TEXT DEFAULT 'unpaid',   -- unpaid | paid | partially_paid
    category        TEXT DEFAULT 'consultation',  -- consultation | lab | pharmacy | other
    insurance_covered INTEGER DEFAULT 0,
    insurance_provider TEXT,
    date_issued     TEXT NOT NULL,
    due_date        TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- ---------------------------------------------------------------------
-- PAYMENTS (payment-history ledger - one row per payment transaction)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id         INTEGER NOT NULL,
    patient_id      INTEGER NOT NULL,
    amount_paid     REAL NOT NULL,
    payment_method  TEXT DEFAULT 'Card',
    paid_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(bill_id),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
);

-- ---------------------------------------------------------------------
-- FAQS
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS faqs (
    faq_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    question        TEXT NOT NULL,
    answer          TEXT NOT NULL,
    category        TEXT
);

-- ---------------------------------------------------------------------
-- HOSPITAL SERVICES (general info)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS hospital_services (
    service_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    description     TEXT,
    availability    TEXT
);

-- ---------------------------------------------------------------------
-- CHAT LOGS (for context / analytics / demo / chat history)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    session_id      TEXT,
    user_message    TEXT,
    bot_response    TEXT,
    intent          TEXT,
    agent           TEXT,
    confidence      REAL,
    sentiment       TEXT,
    entities        TEXT,
    input_mode      TEXT DEFAULT 'text',   -- text | voice
    lang            TEXT DEFAULT 'en',     -- language the user typed/spoke in
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- VOICE LOGS (speech-to-text interactions, for the voice-input feature)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS voice_logs (
    voice_log_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER,
    session_id      TEXT,
    transcript      TEXT NOT NULL,
    recognition_lang TEXT DEFAULT 'en-US',
    used_for_chat   INTEGER DEFAULT 1,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
