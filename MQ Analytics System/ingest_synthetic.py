"""
ingest_synthetic.py
===================
Standalone script that:
  1. Ingests synthetic_ftir_data_v3.xlsx via the existing ETL pipeline
  2. Rebuilds the FAISS index (if applicable/present) to incorporate new records

Usage:
    cd "MQ Analytics System"
    python ingest_synthetic.py
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

SYNTHETIC_EXCEL = r"C:\Users\maury\Downloads\synthetic_ftir_data_v3.xlsx"
DB_PATH = os.path.join(PROJECT_ROOT, "data", "automotive.db")


def main():
    if not os.path.exists(SYNTHETIC_EXCEL):
        print(f"ERROR: Synthetic data file not found: {SYNTHETIC_EXCEL}")
        sys.exit(1)

    print("=" * 60)
    print("STEP 1: Ingesting synthetic_ftir_data_v3.xlsx")
    print("=" * 60)
    
    from core.etl.pipeline import ingest_excel
    new_rows = ingest_excel(SYNTHETIC_EXCEL, DB_PATH)

    if not new_rows:
        print("No new records ingested (all rows may already exist in the database).")

    print("\n" + "=" * 60)
    print("STEP 2: Rebuilding FAISS vector index (if module exists)")
    print("=" * 60)
    
    try:
        from core.database import get_session, Record
        from core.rag.document_builder import build_document_text
        from core.rag.rag_embedder import VectorEmbedder

        session = get_session(DB_PATH)
        rows = session.query(
            Record.id,
            Record.subject_english,
            Record.repair_contents_english,
            Record.causal_parts_name_english,
            Record.outbreak_country,
            Record.product_model_code,
            Record.trouble_code_complaint,
            Record.segmentation,
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
                "repair_contents":   row[2],
                "causal_parts_name": row[3],
            }
            doc_text = build_document_text(record_dict)
            record_ids.append(rec_id)
            texts.append(doc_text)
            metadatas.append({
                "id":           rec_id,
                "country":      row[4],
                "model":        row[5],
                "trouble_code": row[6],
                "segment":      row[7],
            })

        embedder = VectorEmbedder()
        embedder.build_index(record_ids, texts, metadatas)
        print("FAISS index rebuilt successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"FAISS index rebuild failed or not applicable in this project: {e}")

    print("\nAll steps complete. Database is up to date.")

if __name__ == "__main__":
    main()
