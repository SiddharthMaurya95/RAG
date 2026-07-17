from core.utils.decorators import with_logging_and_exceptions
"""
migrate_db.py
=============
One-time, non-destructive migration that adds 14 new columns to the existing
automotive.db records table.

Safe to run multiple times - each ALTER TABLE is wrapped in an individual
try/except so duplicate-column errors are silently ignored.

Usage:
    cd automotive_qa
    python migrate_db.py
"""

import os
import sys
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "automotive.db")

NEW_COLUMNS = [
    ("rank",                        "TEXT",    "Severity/priority: A=Safety/Immobile, B=Other, C=Customer feedback"),
    ("reported_country",            "TEXT",    "Country where the FTIR issue was reported"),
    ("days_used",                   "INTEGER", "Days vehicle was used before incident (from registration date)"),
    ("fpcr_no",                     "TEXT",    "Field Problem Countermeasure Report number"),
    ("sales_dealer",                "TEXT",    "Dealer who sold the vehicle"),
    ("service_dealer",              "TEXT",    "Dealer who serviced the vehicle"),
    ("spec_on_destination",         "TEXT",    "Regional specification of vehicle (INDIA / GULF / EUROPE / etc.)"),
    ("collection_request_date",     "TEXT",    "Date when defective part collection was requested"),
    ("parts_retrieved_date",        "TEXT",    "Date when defective part was received at manufacturing plant"),
    ("person_of_action_judgement",  "TEXT",    "Individual responsible for FTIR investigation and analysis"),
    ("dept_of_action_judgement",    "TEXT",    "MQ department of the action judgement person"),
    ("judgement_date",              "TEXT",    "Date when decision was made by the action judgement person"),
    ("reason_not_sbpr",             "TEXT",    "Justification for closing FTIR without escalating to SBPR"),
    ("approval_judgement_date",     "TEXT",    "Final approval date of the FTIR action judgement"),
    ("root_cause",                  "TEXT",    "Identified root cause of failure derived from complaint, checked results, and causal parts"),
]

NEW_INDICES = [
    ("idx_rank",             "records", "rank"),
    ("idx_reported_country", "records", "reported_country"),
    ("idx_days_used",        "records", "days_used"),
]


@with_logging_and_exceptions
def migrate(db_path):
    if not os.path.exists(db_path):
        print(f"ERROR: Database not found at {db_path}")
        print("Run setup.py first to initialise the database.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cursor = conn.cursor()

    added = 0
    skipped = 0

    print(f"Migrating database: {db_path}\n")
    print("-" * 60)

    for col_name, col_type, description in NEW_COLUMNS:
        try:
            cursor.execute(f"ALTER TABLE records ADD COLUMN {col_name} {col_type};")
            conn.commit()
            print(f"  Added  : {col_name} ({col_type})")
            added += 1
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"  Exists : {col_name} (already present, skipped)")
                skipped += 1
            else:
                conn.rollback()
                conn.close()
                raise

    print("\n" + "-" * 60)
    print(f"Columns added: {added}  |  Already existing (skipped): {skipped}")

    print("\nCreating new indices...")
    for idx_name, table, col in NEW_INDICES:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({col});")
            conn.commit()
            print(f"  Index  : {idx_name} ON {table}({col})")
        except Exception as e:
            print(f"  WARN   : {idx_name} -- {e}")

    conn.close()
    print("\nMigration complete.\n")


if __name__ == "__main__":
    migrate(DB_PATH)
