import os
import glob
from etl.pipeline import ingest_excel
from rag.document_builder import build_document_text
from core.singletons import get_embedder
from core.paths import get_db_path, get_inbox_path

def scan_and_ingest_inbox(inbox_dir="data/inbox", db_path="data/automotive.db"):
    """
    Manually scans the inbox directory for Excel files and ingests them.
    Returns a tuple: (files_processed, total_new_records)
    """
    inbox_dir = get_inbox_path(inbox_dir)
    db_path = get_db_path(db_path)
    os.makedirs(inbox_dir, exist_ok=True)
    
    embedder = get_embedder()
    
    files_processed = 0
    total_new_records = 0
    
    # Find all .xlsx files, skipping temp/lock files
    search_pattern = os.path.join(inbox_dir, "*.xlsx")
    for file_path in glob.glob(search_pattern):
        filename = os.path.basename(file_path)
        if filename.startswith('~$'):
            continue
            
        print(f"Manual ingest detected Excel file: {filename}")
        files_processed += 1
        
        try:
            # 1. Run Ingestion Pipeline
            new_records = ingest_excel(file_path, db_path)
            
            if new_records:
                record_ids = []
                texts = []
                metadatas = []
                
                # 2. Build texts and metadata for the new records
                for rec in new_records:
                    record_ids.append(rec['id'])
                    doc_text = build_document_text({
                        'subject': rec['subject'],
                        'customer_complaint': rec['subject'], # Fallback description
                        'checked_contents': '',
                        'checked_results': rec['checked_results'],
                        'repair_contents': rec['repair_contents'],
                        'causal_parts_name': rec['causal_parts_name']
                    })
                    texts.append(doc_text)
                    
                    metadatas.append({
                        'id': rec['id'],
                        'country': rec['outbreak_country'],
                        'model': rec['product_model_code'],
                        'trouble_code': rec['trouble_code_complaint'],
                        'segment': rec['segmentation']
                    })
                
                # 3. Append to FAISS index
                embedder.append_to_index(record_ids, texts, metadatas)
                
                total_new_records += len(new_records)
                print(f"Successfully processed: {filename} ({len(new_records)} records)")
            else:
                print(f"Processed {filename}: 0 new records (duplicates skipped).")
                
        except Exception as e:
            print(f"Failed to process {filename}: {e}")
            
    return files_processed, total_new_records
