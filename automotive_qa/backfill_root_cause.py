from core.decorators import with_logging_and_exceptions
"""
backfill_root_cause.py
======================
One-time backfill script that computes and populates the `root_cause` column
for all existing records in automotive.db that currently have a NULL value.

The root_cause is derived from structured FTIR fields using the same heuristic
as `etl/pipeline.py:generate_root_cause()`:
  1. Checked Results  — technician's direct inspection finding
  2. Checked Contents + Causal Parts Name — what was inspected and what failed
  3. Customer Complaint — the originally reported symptom
  4. Subject — the FTIR header description as a last resort

Usage:
    cd automotive_qa
    python backfill_root_cause.py
"""

import os
import sys
import re
import sqlite3

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "automotive.db")
sys.path.insert(0, PROJECT_ROOT)


@with_logging_and_exceptions
def _clean(val):
    """Sanitise nan/None string values."""
    if val is None:
        return ''
    val = str(val).strip()
    return val if val.lower() not in ('nan', 'none', '') else ''


@with_logging_and_exceptions
def generate_root_cause(checked_results, checked_contents, causal_parts_name,
                        customer_complaint, subject):
    """
    Derives a concise root-cause statement from structured FTIR columns.
    Returns a single declarative sentence.
    """
    checked_results  = _clean(checked_results)
    checked_contents = _clean(checked_contents)
    part             = _clean(causal_parts_name)
    complaint        = _clean(customer_complaint)
    subject          = _clean(subject)

    primary   = checked_results.split('.')[0]  if checked_results  else ''
    secondary = checked_contents.split('.')[0] if checked_contents else ''
    symptom   = (complaint or subject or 'unspecified complaint').split('.')[0]
    part_clause = f" ({part.lower()})" if part else ''

    if primary:
        root_cause = f"{primary.rstrip('.').lower()}{part_clause}. {symptom.lower()}."
    elif secondary:
        root_cause = f"{secondary.rstrip('.').lower()}{part_clause}. {symptom.lower()}."
    else:
        root_cause = f"{symptom.lower()}{part_clause}."

    root_cause = re.sub(r'\s+', ' ', root_cause).strip()
    return root_cause


@with_logging_and_exceptions
def main():
    # Step 1: Ensure root_cause column exists via migration
    print("=" * 60)
    print("STEP 1: Running database migration (adds root_cause if absent)")
    print("=" * 60)
    from migrate_db import migrate
    migrate(DB_PATH)

    # Step 2: Connect and fetch records missing or containing the old prefix
    print("\n" + "=" * 60)
    print("STEP 2: Fetching records to backfill/update")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id,
               checked_results,
               checked_contents,
               causal_parts_name,
               customer_complaint,
               subject
        FROM records;
    """)
    rows = cursor.fetchall()
    print(f"  Records to backfill: {len(rows)}")

    if not rows:
        print("  All records already have a root_cause value. Nothing to do.")
        conn.close()
        return

    # Step 3: Compute and batch-update root_cause
    print("\n" + "=" * 60)
    print("STEP 3: Computing and writing root_cause values")
    print("=" * 60)

    updates = []
    for row in rows:
        rec_id, checked_results, checked_contents, causal_parts_name, \
            customer_complaint, subject = row
        root_cause = generate_root_cause(
            checked_results, checked_contents, causal_parts_name,
            customer_complaint, subject
        )
        updates.append((root_cause, rec_id))

    cursor.executemany(
        "UPDATE records SET root_cause = ? WHERE id = ?;",
        updates
    )
    conn.commit()
    conn.close()

    print(f"  Successfully updated {len(updates)} record(s) with root_cause.")
    print("\nBackfill complete.")


if __name__ == "__main__":
    main()
