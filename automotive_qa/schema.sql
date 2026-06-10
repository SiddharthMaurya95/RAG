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
    row_hash TEXT UNIQUE,              -- MD5 checksum of row for deduplication
    using_km_int INTEGER,              -- Computed: Cleaned integer km
    report_year INTEGER,               -- Computed: Year of FTIR report
    report_month INTEGER,              -- Computed: Month of FTIR report
    is_resolved INTEGER DEFAULT 0,     -- Computed: 1 if resolved, 0 otherwise
    has_sbpr INTEGER DEFAULT 0,        -- Computed: 1 if has SBPR number, 0 otherwise
    summary TEXT,                      -- Computed: 2-sentence LLM/heuristic summary
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table for session authentication
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat history table
CREATE TABLE IF NOT EXISTS chat_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL,                -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
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

-- Materialized View 5: Escalations dashboard (Poor quality AND Unresolved problem)
CREATE TABLE IF NOT EXISTS mv_escalations (
    id INTEGER PRIMARY KEY,
    ftir_no TEXT,
    subject TEXT,
    reported_company TEXT,
    outbreak_country TEXT,
    trouble_code_complaint TEXT,
    quality TEXT,
    problem_solved TEXT
);

-- Key performance indices (9 indices covering 95% of filter patterns)
CREATE INDEX IF NOT EXISTS idx_outbreak_country ON records(outbreak_country);
CREATE INDEX IF NOT EXISTS idx_product_model_code ON records(product_model_code);
CREATE INDEX IF NOT EXISTS idx_segmentation ON records(segmentation);
CREATE INDEX IF NOT EXISTS idx_trouble_code_complaint ON records(trouble_code_complaint);
CREATE INDEX IF NOT EXISTS idx_status ON records(status);
CREATE INDEX IF NOT EXISTS idx_quality ON records(quality);
CREATE INDEX IF NOT EXISTS idx_repair_status ON records(repair_status);
CREATE INDEX IF NOT EXISTS idx_using_km_int ON records(using_km_int);
CREATE INDEX IF NOT EXISTS idx_report_year ON records(report_year);
