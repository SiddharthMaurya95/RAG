import os
import sys
import sqlite3
import subprocess
import requests

def create_folders():
    """Create directory structure for the application."""
    dirs = [
        "data",
        "data/inbox",
        "models",
        "etl",
        "nlp",
        "rag",
        "analytics",
        "viz",
        "reports",
        "llm",
        "core",
        "auth",
        "app"
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

def download_spacy_model():
    """Downloads the English small spaCy model."""
    print("Downloading spaCy model 'en_core_web_sm'...")
    try:
        subprocess.run(
            [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
            check=True
        )
        print("spaCy model downloaded successfully.")
    except Exception as e:
        print(f"Failed to download spaCy model: {e}")
        print("Proceeding - NLP processor will fall back to regex-based extraction.")

def download_qwen_model(model_dir):
    """Downloads the Qwen 2.5-7B GGUF model from Hugging Face if not present."""
    model_name = "qwen2.5-7b-instruct-q4_k_m.gguf"
    dest_path = os.path.join(model_dir, model_name)
    url = f"https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/{model_name}"
    
    if os.path.exists(dest_path):
        print(f"Model already exists at: {dest_path}")
        return
        
    print(f"Downloading model {model_name} (approx. 4.7 GB). This may take several minutes...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024 # 1 MB chunks
        
        downloaded = 0
        with open(dest_path, 'wb') as f:
            for data in response.iter_content(block_size):
                f.write(data)
                downloaded += len(data)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    sys.stdout.write(f"\rProgress: {percent:.2f}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")
                    sys.stdout.flush()
        print("\nModel downloaded successfully.")
    except Exception as e:
        print(f"\nError downloading model: {e}")
        print(f"Please manually download the model from {url} and place it in the '{model_dir}' folder.")
        # Do not raise exception here, let the setup continue

def run_initial_etl(excel_source, db_path):
    """Ingests the initial Excel data sheet and builds the vector database index."""
    print("Starting initial ETL Ingestion...")
    # Add project root to sys.path so we can import modules
    sys.path.append(os.getcwd())
    
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
    db_path = "data/automotive.db"
    schema_path = "schema.sql"
    model_dir = "models"
    
    # Check if ftir_dummy.xlsx exists in root (we copied it there)
    excel_source = "../ftir_dummy.xlsx"
    if not os.path.exists(excel_source):
        # Check inside the current dir too
        excel_source = "ftir_dummy.xlsx"
        if not os.path.exists(excel_source):
            # Check one more parent folder
            excel_source = "../../ftir_dummy.xlsx"
            
    print(f"Detected excel source path: {excel_source}")
    
    create_folders()
    init_database(db_path, schema_path)
    download_spacy_model()
    download_qwen_model(model_dir)
    run_initial_etl(excel_source, db_path)
    print("Project setup completed successfully!")
