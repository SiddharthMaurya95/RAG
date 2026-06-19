import os
import sys
import sqlite3
import subprocess
import requests

def create_folders(project_root):
    """Create directory structure for the application."""
    dirs = [
        os.path.join(project_root, "data"),
        os.path.join(project_root, "data", "inbox"),
        os.path.join(project_root, "models"),
        os.path.join(project_root, "reports_cache")
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("Folder structure verified.")

def init_database(db_path, schema_path):
    """Executes schema.sql to initialize database tables and indexes."""
    print(f"Initializing database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
        
    try:
        # SQLite executescript allows running multiple statements
        cursor.executescript(schema_sql)
        conn.commit()
        print("Database schema loaded successfully.")
    except Exception as e:
        print(f"Error loading schema: {e}")
        sys.exit(1)
    finally:
        conn.close()

# def download_spacy_model():
#     """Downloads the English small spaCy model."""
#     print("Downloading spaCy model 'en_core_web_sm'...")
#     try:
#         subprocess.run(
#             [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
#             check=True
#         )
#         print("spaCy model downloaded successfully.")
#     except Exception as e:
#         print(f"Failed to download spaCy model: {e}")
#         print("Proceeding - NLP processor will fall back to regex-based extraction.")



def run_initial_etl(excel_source, db_path, project_root):
    """Ingests the initial Excel data sheet and builds the vector database index."""
    print("Starting initial ETL Ingestion...")
    # Add project root to sys.path so we can import modules
    sys.path.append(project_root)
    
    from etl.pipeline import ingest_excel
    from rag.document_builder import build_document_text
    from rag.embedder import VectorEmbedder
    
    # 1. Ingest Excel rows into database
    new_rows = ingest_excel(excel_source, db_path)
    if not new_rows:
        print("No new records ingested or records already existed.")
        return
        
    # 2. Build initial FAISS Index
    print("Building initial FAISS vector index...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, subject, customer_complaint, checked_contents, 
               checked_results, repair_contents, causal_parts_name,
               outbreak_country, product_model_code, trouble_code_complaint, segmentation
        FROM records;
    """)
    rows = cursor.fetchall()
    conn.close()
    
    record_ids = []
    texts = []
    metadatas = []
    
    for row in rows:
        rec_id = row[0]
        # map db columns to dict format expected by build_document_text
        record_dict = {
            'subject': row[1],
            'customer_complaint': row[2],
            'checked_contents': row[3],
            'checked_results': row[4],
            'repair_contents': row[5],
            'causal_parts_name': row[6]
        }
        doc_text = build_document_text(record_dict)
        
        record_ids.append(rec_id)
        texts.append(doc_text)
        
        # Parallel metadata for routing filtering
        metadatas.append({
            'id': rec_id,
            'country': row[7],
            'model': row[8],
            'trouble_code': row[9],
            'segment': row[10]
        })
        
    embedder = VectorEmbedder()
    # Build and train FAISS index on 384-dimensional cosine metrics
    embedder.build_index(record_ids, texts, metadatas, nlist=100)
    print("Initial ETL and FAISS index setup complete.")

if __name__ == "__main__":
    # Get absolute path to the directory containing setup.py (automotive_qa)
    project_root = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(project_root)
    
    db_path = os.path.join(project_root, "data", "automotive.db")
    schema_path = os.path.join(project_root, "schema.sql")
    model_dir = os.path.join(project_root, "models")
    
    # Check if ftir_dummy.xlsx exists in repository root or package folder
    excel_source = os.path.join(repo_root, "ftir_dummy.xlsx")
    if not os.path.exists(excel_source):
        excel_source = os.path.join(project_root, "ftir_dummy.xlsx")
            
    print(f"Detected excel source path: {excel_source}")
    
    create_folders(project_root)
    init_database(db_path, schema_path)
    # download_spacy_model()
    run_initial_etl(excel_source, db_path, project_root)
    print("Project setup completed successfully!")
