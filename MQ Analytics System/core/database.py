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

def get_engine(db_path="data/automotive.db"):
    """
    Returns or creates the SQLAlchemy engine for the given DB path.
    Enables WAL mode and normal synchronous behavior for SQLite.
    """
    global _engine
    abs_db_path = get_db_path(db_path)
    
    # Check if engine exists and is for the same path
    if _engine is None or _engine.url.database != abs_db_path:
        db_url = f"sqlite:///{abs_db_path}"
        _engine = create_engine(db_url, connect_args={"timeout": 30})
        
        # Listen to connect event to set journal mode to WAL and synchronous to NORMAL
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()
            
    return _engine

def get_session(db_path="data/automotive.db"):
    """
    Creates and returns a new SQLAlchemy session.
    """
    global _SessionFactory
    engine = get_engine(db_path)
    if _SessionFactory is None or _SessionFactory.kw['bind'] != engine:
        _SessionFactory = sessionmaker(bind=engine)
    return _SessionFactory()


class Record(Base):
    __tablename__ = 'records'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sbpr_no = Column(String, nullable=True)
    ftir_no = Column(String, unique=True, nullable=True)
    ftir_report_date = Column(String, nullable=True)
    reply_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    fc_ok = Column(String, nullable=True)
    product_model_code = Column(String, nullable=True)
    sales_model_code = Column(String, nullable=True)
    segmentation = Column(String, nullable=True)
    vin = Column(String, nullable=True)
    engine_no = Column(String, nullable=True)
    transmission_no = Column(String, nullable=True)
    date_registered = Column(String, nullable=True)
    date_of_incident = Column(String, nullable=True)
    using_time_km = Column(String, nullable=True)
    reported_company = Column(String, nullable=True)
    issued_company = Column(String, nullable=True)
    outbreak_country = Column(String, nullable=True)
    manufacturer_factory = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    c_measure = Column(String, nullable=True)
    customer_complaint = Column(String, nullable=True)
    trouble_code_complaint = Column(String, nullable=True)
    trouble_code_defect = Column(String, nullable=True)
    checked_contents = Column(String, nullable=True)
    checked_results = Column(String, nullable=True)
    repair_status = Column(String, nullable=True)
    repair_contents = Column(String, nullable=True)
    # problem_solved = Column(String, nullable=True)
    action_judgement = Column(String, nullable=True)
    causal_parts_no = Column(String, nullable=True)
    causal_parts_name = Column(String, nullable=True)
    # supplier_of_causal_parts = Column(String, nullable=True)
    production_base = Column(String, nullable=True)
    parts_availability = Column(String, nullable=True)
    # file_name = Column(String, nullable=True)
    quality = Column(String, nullable=True)
    # ── New columns (v2 schema) ───────────────────────────────────────────────
    rank = Column(String, nullable=True)                       # A/B/C severity ranking
    reported_country = Column(String, nullable=True)           # Country where issue was reported
    days_used = Column(Integer, nullable=True)                 # Days vehicle used before incident
    fpcr_no = Column(String, nullable=True)                    # Field Problem Countermeasure Report No.
    sales_dealer = Column(String, nullable=True)               # Dealer who sold the vehicle
    service_dealer = Column(String, nullable=True)             # Dealer who serviced the vehicle
    spec_on_destination = Column(String, nullable=True)        # Regional spec (INDIA / GULF / etc.)
    collection_request_date = Column(String, nullable=True)    # Date part collection was requested
    parts_retrieved_date = Column(String, nullable=True)       # Date defective part received at plant
    person_of_action_judgement = Column(String, nullable=True) # Investigator name
    department_of_action_judgement = Column(String, nullable=True)   # MQ department of investigator
    judgement_date = Column(String, nullable=True)             # Decision date by investigator
    reason_of_not_to_file_as_an_sbpr = Column(String, nullable=True)            # Justification for not filing SBPR
    approval_judgement_date = Column(String, nullable=True)    # Final FTIR approval date
    # ── Computed / metadata columns ──────────────────────────────────────────
    row_hash = Column(String, unique=True, nullable=True)
    using_km_int = Column(Integer, nullable=True)
    report_year = Column(Integer, nullable=True)
    report_month = Column(Integer, nullable=True)
    is_resolved = Column(Integer, default=0)
    has_sbpr = Column(Integer, default=0)
    summary = Column(Text, nullable=True)
    # root_cause = Column(Text, nullable=True)        # Root cause of failure derived from complaint & investigation results
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
        Index('idx_rank', 'rank'),
        Index('idx_reported_country', 'reported_country'),
        Index('idx_days_used', 'days_used'),
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
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    intent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        Index('idx_chat_history_session', 'session_id'),
        Index('idx_chat_history_user', 'user_id'),
    )


class QueryCache(Base):
    __tablename__ = 'query_cache'
    
    query_hash = Column(String, primary_key=True)
    user_id = Column(Integer, primary_key=True, default=0)  # 0 represents globally shared cache
    result_json = Column(Text, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class EmbeddingCache(Base):
    __tablename__ = 'embedding_cache'
    
    text_hash = Column(String, primary_key=True)
    embedding_blob = Column(LargeBinary, nullable=False)


# Materialized View mappings (read-write tables in SQLite)

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
