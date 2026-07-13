-- Enable Write-Ahead Logging (WAL) mode for better concurrency
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

-- Core table for FTIR records
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sbpr_no TEXT,
    ftir_no TEXT UNIQUE,
    ftir_report_date TEXT,
    reply_date TEXT,
    status TEXT,
    fc_ok TEXT,
    product_model_code TEXT,
    sales_model_code TEXT,
    segmentation TEXT,
    vin TEXT,
    engine_no TEXT,
    transmission_no TEXT,
    date_registered TEXT,
    date_of_incident TEXT,
    using_time_km TEXT,
    reported_company TEXT,
    issued_company TEXT,
    outbreak_country TEXT,
    manufacturer_factory TEXT,
    subject TEXT,
    c_measure TEXT,
    customer_complaint TEXT,
    trouble_code_complaint TEXT,
    trouble_code_defect TEXT,
    checked_contents TEXT,
    checked_results TEXT,
    repair_status TEXT,
    repair_contents TEXT,
    problem_solved TEXT,
    action_judgement TEXT,
    causal_parts_no TEXT,
    causal_parts_name TEXT,
    supplier_of_causal_parts TEXT,
    production_base TEXT,
    parts_availability TEXT,
    file_name TEXT,
    quality TEXT,
    -- ── New columns (v2 schema) ───────────────────────────────────────────────
    rank TEXT,                          -- Severity: A=Safety/Immobile, B=Other, C=Customer feedback
    reported_country TEXT,              -- Country where the issue was reported
    days_used INTEGER,                  -- Days vehicle was used before incident (from registration)
    fpcr_no TEXT,                       -- Field Problem Countermeasure Report number
    sales_dealer TEXT,                  -- Dealer who sold the vehicle
    service_dealer TEXT,                -- Dealer who serviced the vehicle
    spec_on_destination TEXT,           -- Regional specification of vehicle (e.g. INDIA, GULF)
    collection_request_date TEXT,       -- Date when defective part collection was requested
    parts_retrieved_date TEXT,          -- Date when defective part was received at plant
    person_of_action_judgement TEXT,    -- Individual responsible for FTIR investigation
    dept_of_action_judgement TEXT,      -- MQ department of the action judgement person
    judgement_date TEXT,                -- Date decision was made by person of action judgement
    reason_not_sbpr TEXT,               -- Justification for closing FTIR without filing as SBPR
    approval_judgement_date TEXT,       -- Final approval date of the FTIR action judgement
    -- ── Computed / metadata columns ───────────────────────────────────────────
    row_hash TEXT UNIQUE,              -- MD5 checksum of row for deduplication
    using_km_int INTEGER,              -- Computed: Cleaned integer km
    report_year INTEGER,               -- Computed: Year of FTIR report
    report_month INTEGER,              -- Computed: Month of FTIR report
    is_resolved INTEGER DEFAULT 0,     -- Computed: 1 if resolved, 0 otherwise
    has_sbpr INTEGER DEFAULT 0,        -- Computed: 1 if has SBPR number, 0 otherwise
    summary TEXT,                      -- Computed: 2-sentence LLM/heuristic summary
    root_cause TEXT,                   -- Computed: Identified root cause derived from complaint and checked results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table for session authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Chat history table
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_id INTEGER,
    role TEXT NOT NULL,                -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);


-- Analytics & query caching table
CREATE TABLE IF NOT EXISTS query_cache (
    query_hash TEXT NOT NULL,
    user_id INTEGER NOT NULL DEFAULT 0, -- 0 represents globally shared cache
    result_json TEXT NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    PRIMARY KEY(query_hash, user_id)
);

-- Embeddings caching table
CREATE TABLE IF NOT EXISTS embedding_cache (
    text_hash TEXT PRIMARY KEY,
    embedding_blob BLOB NOT NULL
);

-- Materialized View 1: Month/Year by Country count
CREATE TABLE IF NOT EXISTS mv_country_month (
    outbreak_country TEXT,
    report_year INTEGER,
    report_month INTEGER,
    record_count INTEGER,
    PRIMARY KEY(outbreak_country, report_year, report_month)
);

-- Materialized View 2: Trouble code frequency counts
CREATE TABLE IF NOT EXISTS mv_trouble_codes (
    trouble_code TEXT PRIMARY KEY,
    record_count INTEGER
);

-- Materialized View 3: Reported company (dealer) count of failures
CREATE TABLE IF NOT EXISTS mv_dealer_summary (
    reported_company TEXT PRIMARY KEY,
    record_count INTEGER
);

-- Materialized View 4: Counts by quality rating
CREATE TABLE IF NOT EXISTS mv_quality_dist (
    quality TEXT PRIMARY KEY,
    record_count INTEGER
);


-- Key performance indices (12 indices covering primary filter patterns)
CREATE INDEX IF NOT EXISTS idx_outbreak_country ON records(outbreak_country);
CREATE INDEX IF NOT EXISTS idx_product_model_code ON records(product_model_code);
CREATE INDEX IF NOT EXISTS idx_segmentation ON records(segmentation);
CREATE INDEX IF NOT EXISTS idx_trouble_code_complaint ON records(trouble_code_complaint);
CREATE INDEX IF NOT EXISTS idx_status ON records(status);
CREATE INDEX IF NOT EXISTS idx_quality ON records(quality);
CREATE INDEX IF NOT EXISTS idx_repair_status ON records(repair_status);
CREATE INDEX IF NOT EXISTS idx_using_km_int ON records(using_km_int);
CREATE INDEX IF NOT EXISTS idx_report_year ON records(report_year);
CREATE INDEX IF NOT EXISTS idx_rank ON records(rank);
CREATE INDEX IF NOT EXISTS idx_reported_country ON records(reported_country);
CREATE INDEX IF NOT EXISTS idx_days_used ON records(days_used);

-- Chat & Session indexing to speed up queries and deletions
CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_user ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- MIGRATION: Add new columns to existing databases (safe — ignored if column
-- already exists via try/catch in migrate_db.py; this block is for reference)
-- ─────────────────────────────────────────────────────────────────────────────
-- ALTER TABLE records ADD COLUMN rank TEXT;
-- ALTER TABLE records ADD COLUMN reported_country TEXT;
-- ALTER TABLE records ADD COLUMN days_used INTEGER;
-- ALTER TABLE records ADD COLUMN fpcr_no TEXT;
-- ALTER TABLE records ADD COLUMN sales_dealer TEXT;
-- ALTER TABLE records ADD COLUMN service_dealer TEXT;
-- ALTER TABLE records ADD COLUMN spec_on_destination TEXT;
-- ALTER TABLE records ADD COLUMN collection_request_date TEXT;
-- ALTER TABLE records ADD COLUMN parts_retrieved_date TEXT;
-- ALTER TABLE records ADD COLUMN person_of_action_judgement TEXT;
-- ALTER TABLE records ADD COLUMN dept_of_action_judgement TEXT;
-- ALTER TABLE records ADD COLUMN judgement_date TEXT;
-- ALTER TABLE records ADD COLUMN reason_not_sbpr TEXT;
-- ALTER TABLE records ADD COLUMN approval_judgement_date TEXT;


