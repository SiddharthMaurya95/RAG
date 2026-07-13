# =====================================================
# ✅ DATABASE & SCHEMA
# =====================================================
import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, LargeBinary, ForeignKey, Index, event
from sqlalchemy.orm import declarative_base, sessionmaker
from core.paths import get_db_path

Base = declarative_base()

_engine = None
_SessionFactory = None

def get_engine(db_path=None):
    """Returns or creates the SQLAlchemy engine for the given DB path."""
    global _engine
    if db_path is None:
        from core.config import DB_PATH
        db_path = DB_PATH
        
    if _engine is None or _engine.url.database != db_path:
        db_url = f"sqlite:///{db_path}"
        _engine = create_engine(db_url, connect_args={"timeout": 30})
        
        # Configure WAL journal mode for optimal SQLite concurrency
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()
            
    return _engine

def get_session(db_path=None):
    """Creates and returns a new SQLAlchemy database session."""
    global _SessionFactory
    engine = get_engine(db_path)
    if _SessionFactory is None or _SessionFactory.kw['bind'] != engine:
        _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory()


class Record(Base):
    __tablename__ = 'records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # original / new columns from Excel
    sbpr_no = Column(String, nullable=True)
    c_measure = Column(String, nullable=True)
    ftir_no = Column(String, unique=True, nullable=True)
    product_model_code = Column(String, nullable=True)
    sales_model_code = Column(String, nullable=True)
    segmentation = Column(String, nullable=True)
    subject_english = Column(String, nullable=True)
    subject_your_language = Column(String, nullable=True)
    causal_parts_no = Column(String, nullable=True)
    rank = Column(String, nullable=True)
    reported_country = Column(String, nullable=True)
    vin = Column(String, nullable=True)
    report_company = Column(String, nullable=True)
    issued_company = Column(String, nullable=True)
    ftir_report_date = Column(String, nullable=True)
    reply_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    fc_ok = Column(String, nullable=True)
    date_registered = Column(String, nullable=True)
    date_of_incident = Column(String, nullable=True)
    mileage_using_time = Column(String, nullable=True)
    days_used = Column(Integer, nullable=True)
    deliberation = Column(String, nullable=True)
    pending_due_date = Column(String, nullable=True)
    latest_meeting_date = Column(String, nullable=True)
    deliberation_base = Column(String, nullable=True)
    transaction_base = Column(String, nullable=True)
    production_base = Column(String, nullable=True)
    requested_bases_ibcr = Column(String, nullable=True)
    drawing_parts_no = Column(String, nullable=True)
    fpcr_no = Column(String, nullable=True)
    engine_no = Column(String, nullable=True)
    transmission_no = Column(String, nullable=True)
    outbreak_country = Column(String, nullable=True)
    trouble_code_complaint = Column(String, nullable=True)
    trouble_code_defect = Column(String, nullable=True)
    sales_dealer = Column(String, nullable=True)
    service_dealer = Column(String, nullable=True)
    spec_on_destination = Column(String, nullable=True)
    vehicles_of_same_incident = Column(String, nullable=True)
    parts_availability = Column(String, nullable=True)
    causal_parts_name_english = Column(String, nullable=True)
    causal_parts_name_your_language = Column(String, nullable=True)
    collection_request_date = Column(String, nullable=True)
    parts_retrieved_date = Column(String, nullable=True)
    manufacturer_factory = Column(String, nullable=True)
    issue_no_report_co = Column(String, nullable=True)
    person_of_action_judgement = Column(String, nullable=True)
    department_of_action_judgement = Column(String, nullable=True)
    judgement_date = Column(String, nullable=True)
    action_judgement = Column(String, nullable=True)
    reason_of_not_to_file_as_an_sbpr = Column(String, nullable=True)
    remarkable_problems = Column(String, nullable=True)
    repair_contents_english = Column(String, nullable=True)
    repair_contents_your_language = Column(String, nullable=True)
    approval_judgement_date = Column(String, nullable=True)
    taken_out_parts1 = Column(String, nullable=True)
    taken_out_date1 = Column(String, nullable=True)
    taken_out_parts2 = Column(String, nullable=True)
    taken_out_date2 = Column(String, nullable=True)
    taken_out_parts3 = Column(String, nullable=True)
    taken_out_date3 = Column(String, nullable=True)
    tsr_report_date = Column(String, nullable=True)
    sbpr = Column(String, nullable=True)
    requested_bases_ibcr_start_date = Column(String, nullable=True)
    account_of_nonacceptance = Column(String, nullable=True)
    account_of_nonacceptance_details_english = Column(String, nullable=True)
    account_of_nonacceptance_details_your_language = Column(String, nullable=True)
    ftir_date_received = Column(String, nullable=True)
    parts_dispatch_date = Column(String, nullable=True)
    parts_dispatch_status = Column(String, nullable=True)

    # Legacy mappings (for backward compatibility with SQL generator / engine queries)
    subject = Column(String, nullable=True)
    customer_complaint = Column(String, nullable=True)
    checked_contents = Column(String, nullable=True)
    checked_results = Column(String, nullable=True)
    repair_status = Column(String, nullable=True)
    repair_contents = Column(String, nullable=True)
    causal_parts_name = Column(String, nullable=True)
    using_time_km = Column(String, nullable=True)
    quality = Column(String, nullable=True)
    reported_company = Column(String, nullable=True)

    # Derived/custom columns
    row_hash = Column(String, unique=True, nullable=True)
    using_km_int = Column(Integer, nullable=True)
    report_year = Column(Integer, nullable=True)
    report_month = Column(Integer, nullable=True)
    is_resolved = Column(Integer, default=0)
    has_sbpr = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        Index('idx_outbreak_country', 'outbreak_country'),
        Index('idx_product_model_code', 'product_model_code'),
        Index('idx_segmentation', 'segmentation'),
        Index('idx_trouble_code_complaint', 'trouble_code_complaint'),
        Index('idx_status', 'status'),
        Index('idx_quality', 'quality'),
        Index('idx_repair_status', 'repair_status'),
        Index('idx_using_km_int', 'using_km_int'),
        Index('idx_report_year', 'report_year'),
    )


class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        Index('idx_chat_sessions_user', 'user_id'),
    )


class ChatHistory(Base):
    __tablename__ = 'chat_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    session_id = Column(Integer, ForeignKey('chat_sessions.id', ondelete='CASCADE'), nullable=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        Index('idx_chat_history_session', 'session_id'),
        Index('idx_chat_history_user', 'user_id'),
    )


class QueryCache(Base):
    __tablename__ = 'query_cache'
    
    query_hash = Column(String, primary_key=True)
    user_id = Column(Integer, primary_key=True, default=0)
    result_json = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class EmbeddingCache(Base):
    __tablename__ = 'embedding_cache'
    
    text_hash = Column(String, primary_key=True)
    embedding_blob = Column(LargeBinary, nullable=False)


class MVCountryMonth(Base):
    __tablename__ = 'mv_country_month'
    
    outbreak_country = Column(String, primary_key=True)
    report_year = Column(Integer, primary_key=True)
    report_month = Column(Integer, primary_key=True)
    record_count = Column(Integer)


class MVTroubleCodes(Base):
    __tablename__ = 'mv_trouble_codes'
    
    trouble_code = Column(String, primary_key=True)
    record_count = Column(Integer)


class MVDealerSummary(Base):
    __tablename__ = 'mv_dealer_summary'
    
    reported_company = Column(String, primary_key=True)
    record_count = Column(Integer)


class MVQualityDist(Base):
    __tablename__ = 'mv_quality_dist'
    
    quality = Column(String, primary_key=True)
    record_count = Column(Integer)


def refresh_materialized_views(db_path):
    """Clears and rebuilds all simulated materialized views from the raw 'records' table."""
    conn = get_engine(db_path).raw_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Refresh mv_country_month
        cursor.execute("DELETE FROM mv_country_month;")
        cursor.execute("""
            INSERT INTO mv_country_month (outbreak_country, report_year, report_month, record_count)
            SELECT outbreak_country, report_year, report_month, COUNT(*)
            FROM records
            WHERE outbreak_country IS NOT NULL AND report_year > 0
            GROUP BY outbreak_country, report_year, report_month;
        """)

        # 2. Refresh mv_trouble_codes
        cursor.execute("DELETE FROM mv_trouble_codes;")
        cursor.execute("""
            INSERT INTO mv_trouble_codes (trouble_code, record_count)
            SELECT trouble_code_complaint, COUNT(*)
            FROM records
            WHERE trouble_code_complaint IS NOT NULL
            GROUP BY trouble_code_complaint;
        """)

        # 3. Refresh mv_dealer_summary
        cursor.execute("DELETE FROM mv_dealer_summary;")
        cursor.execute("""
            INSERT INTO mv_dealer_summary (reported_company, record_count)
            SELECT reported_company, COUNT(*)
            FROM records
            WHERE reported_company IS NOT NULL
            GROUP BY reported_company;
        """)

        # 4. Refresh mv_quality_dist
        cursor.execute("DELETE FROM mv_quality_dist;")
        cursor.execute("""
            INSERT INTO mv_quality_dist (quality, record_count)
            SELECT quality, COUNT(*)
            FROM records
            WHERE quality IS NOT NULL
            GROUP BY quality;
        """)

        cursor.execute("COMMIT;")
    except Exception as e:
        cursor.execute("ROLLBACK;")
        print(f"Error refreshing materialized views: {e}")
        raise e
    finally:
        conn.close()
