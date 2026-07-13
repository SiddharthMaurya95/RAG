"""
ingest_synthetic.py
===================
Standalone script that:
  1. Runs the DB migration (adds new columns to automotive.db)
  2. Ingests synthetic_ftir_data_v3.xlsx via the existing ETL pipeline
  3. Rebuilds the FAISS index to incorporate new records

Usage:
    cd automotive_qa
    python ingest_synthetic.py
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

SYNTHETIC_EXCEL = r"C:\Users\maury\Downloads\synthetic_ftir_data_v3.xlsx"
DB_PATH = os.path.join(PROJECT_ROOT, "data", "automotive.db")
MODEL_DIR = os.path.join(PROJECT_ROOT, "models")


def main():
    # ── Step 1: Run DB migration ─────────────────────────────────────────────
    print("=" * 60)
    print("STEP 1: Running database migration")
    print("=" * 60)
    from migrate_db import migrate
    migrate(DB_PATH)

    # ── Step 2: Validate synthetic file exists ───────────────────────────────
    if not os.path.exists(SYNTHETIC_EXCEL):
        print(f"ERROR: Synthetic data file not found: {SYNTHETIC_EXCEL}")
        print("Please run the generation engine first.")
        sys.exit(1)

    # ── Step 3: Ingest Excel into database ──────────────────────────────────
    print("=" * 60)
    print("STEP 2: Ingesting synthetic_ftir_data_v3.xlsx")
    print("=" * 60)
    from etl.pipeline import ingest_excel
    new_rows = ingest_excel(SYNTHETIC_EXCEL, DB_PATH)

    if not new_rows:
        print("No new records ingested (all rows may already exist in the database).")
        print("Proceeding to index rebuild anyway...")

    print(f"\nIngested {len(new_rows)} new records.")

    # ── Step 4: Rebuild FAISS index ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("STEP 3: Rebuilding FAISS vector index")
    print("=" * 60)

    from core.database import get_session, Record
    from rag.document_builder import build_document_text
    from rag.embedder import VectorEmbedder

    session = get_session(DB_PATH)
    rows = session.query(
        Record.id,
        Record.subject,
        Record.customer_complaint,
        Record.checked_contents,
        Record.checked_results,
        Record.repair_contents,
        Record.causal_parts_name,
        Record.outbreak_country,
        Record.product_model_code,
        Record.trouble_code_complaint,
        Record.segmentation,
        Record.root_cause,
    ).all()
    session.close()

    print(f"Total records in DB for indexing: {len(rows)}")

    record_ids = []
    texts = []
    metadatas = []

    for row in rows:
        rec_id = row[0]
        record_dict = {
            "subject":           row[1],
            "customer_complaint": row[2],
            "checked_contents":  row[3],
            "checked_results":   row[4],
            "repair_contents":   row[5],
            "causal_parts_name": row[6],
            "root_cause":        row[11],
        }
        doc_text = build_document_text(record_dict)
        record_ids.append(rec_id)
        texts.append(doc_text)
        metadatas.append({
            "id":           rec_id,
            "country":      row[7],
            "model":        row[8],
            "trouble_code": row[9],
            "segment":      row[10],
        })

    embedder = VectorEmbedder()
    embedder.build_index(record_ids, texts, metadatas, nlist=100)
    print("FAISS index rebuilt successfully.")
    print("\nAll steps complete. Database and index are up to date.")


if __name__ == "__main__":
    main()
