import os
import sys
import sqlite3
import numpy as np

# Set up paths
sys.path.append(os.path.join(os.path.abspath("."), "automotive_qa"))

# Monkey-patch SQLite cache writes BEFORE importing cache/embedder to avoid disk write locks/sync overhead
from core.cache import EmbeddingCache
EmbeddingCache.set = lambda self, text, embedding: None

from core.paths import get_db_path
from core.singletons import get_embedder
import rag.document_builder as db_mod

# Formulas to test
formulas = [
    # 1. Subject + Complaint + Part + TC + First sentence of results
    {
        "name": "Subj + Comp + Part + TC + First Results",
        "func": lambda r: (
            f"Issue: {db_mod._clean(r.get('subject'))}. "
            f"Complaint: {db_mod._clean(r.get('customer_complaint'))}. "
            f"Causal Part: {db_mod._clean(r.get('causal_parts_name'))}. "
            f"Trouble Code: {db_mod._clean(r.get('trouble_code_complaint'))}. "
            f"Findings: {db_mod._clean(r.get('checked_results')).split('.')[0]}."
        )
    },
    # 2. Focus on keywords and minimal context
    {
        "name": "Keywords focus (Subj + Part + TC)",
        "func": lambda r: (
            f"Vehicle issue: {db_mod._clean(r.get('subject'))}. "
            f"Causal Part: {db_mod._clean(r.get('causal_parts_name'))}. "
            f"Trouble Code: {db_mod._clean(r.get('trouble_code_complaint'))}."
        )
    },
    # 3. Old heuristic summary logic
    {
        "name": "Old Heuristic",
        "func": lambda r: (
            f"Issue reported was '{db_mod._clean(r.get('subject')) or 'Vehicle issue'}', related to "
            f"{f'causal part {db_mod._clean(r.get('causal_parts_name')).lower()}' if r.get('causal_parts_name') else 'causal component'}. "
            f"Checked results found '{db_mod._clean(r.get('checked_results')).split('.')[0] or 'inspected by technician'}', "
            f"and technician action was '{db_mod._clean(r.get('repair_contents')).split('.')[0] or 'repaired'}'."
        )
    },
    # 4. Old Heuristic + Trouble Code
    {
        "name": "Old Heuristic + Trouble Code",
        "func": lambda r: (
            f"Issue reported was '{db_mod._clean(r.get('subject')) or 'Vehicle issue'}', related to "
            f"{f'causal part {db_mod._clean(r.get('causal_parts_name')).lower()}' if r.get('causal_parts_name') else 'causal component'}. "
            f"Trouble code: {db_mod._clean(r.get('trouble_code_complaint'))}. "
            f"Checked results found '{db_mod._clean(r.get('checked_results')).split('.')[0] or 'inspected by technician'}', "
            f"and technician action was '{db_mod._clean(r.get('repair_contents')).split('.')[0] or 'repaired'}'."
        )
    },
    # 5. Clean, condensed structural template
    {
        "name": "Clean structural context (Subj + Comp + Part + TC + Repair)",
        "func": lambda r: (
            f"Vehicle issue is {db_mod._clean(r.get('subject'))}. "
            f"Causal part is {db_mod._clean(r.get('causal_parts_name'))}. "
            f"Trouble code is {db_mod._clean(r.get('trouble_code_complaint'))}. "
            f"Technician repaired by {db_mod._clean(r.get('repair_contents')).split('.')[0]}."
        )
    }
]

# Fetch evaluation samples (mimicking evaluate_system.py)
db_path = get_db_path("data/automotive.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT id, subject, customer_complaint, causal_parts_name, trouble_code_complaint, outbreak_country, product_model_code
    FROM records
    WHERE subject IS NOT NULL AND subject != ''
      AND causal_parts_name IS NOT NULL AND causal_parts_name != ''
      AND trouble_code_complaint IS NOT NULL AND trouble_code_complaint != ''
      AND outbreak_country IS NOT NULL AND outbreak_country != ''
    ORDER BY RANDOM()
    LIMIT 50;
""")
eval_rows = cursor.fetchall()

cursor.execute("SELECT id FROM records;")
all_ids = [r[0] for r in cursor.fetchall()]
conn.close()

# Re-read all records from DB for indexing
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT id, subject, customer_complaint, checked_contents, 
           checked_results, repair_contents, causal_parts_name,
           outbreak_country, product_model_code, trouble_code_complaint, segmentation,
           ftir_no, sbpr_no, vin, engine_no, transmission_no, summary
    FROM records;
""")
db_rows = cursor.fetchall()
conn.close()

# Function to run evaluation on a specific summary builder
def evaluate_formula(formula_func):
    # Rebuild metadata and texts
    record_ids = []
    texts = []
    metadatas = []
    
    for row in db_rows:
        rec_id = row[0]
        record_dict = {
            'subject': row[1],
            'customer_complaint': row[2],
            'checked_contents': row[3],
            'checked_results': row[4],
            'repair_contents': row[5],
            'causal_parts_name': row[6],
            'outbreak_country': row[7],
            'product_model_code': row[8],
            'trouble_code_complaint': row[9],
            'segmentation': row[10],
            'ftir_no': row[11],
            'sbpr_no': row[12],
            'vin': row[13],
            'engine_no': row[14],
            'transmission_no': row[15],
            'summary': row[16]
        }
        
        # Override the summary field dynamically
        summary = formula_func(record_dict)
        
        # Build document text
        doc_parts = []
        if summary:
            doc_parts.append(summary)
        
        country = db_mod._clean(record_dict.get('outbreak_country'))
        model = db_mod._clean(record_dict.get('product_model_code'))
        tc = db_mod._clean(record_dict.get('trouble_code_complaint'))
        segment = db_mod._clean(record_dict.get('segmentation'))
        part = db_mod._clean(record_dict.get('causal_parts_name'))
        
        if part:
            doc_parts.append(f"Causal Part: {part}")
        if country:
            doc_parts.append(f"Country: {country}")
        if model:
            doc_parts.append(f"Model: {model}")
        if tc:
            doc_parts.append(f"Trouble Code: {tc}")
        if segment:
            doc_parts.append(f"Segmentation: {segment}")
            
        doc_text = "\n".join(doc_parts)
        
        record_ids.append(rec_id)
        texts.append(doc_text)
        metadatas.append({
            'id': rec_id,
            'country': row[7],
            'model': row[8],
            'trouble_code': row[9],
            'segment': row[10]
        })
        
    embedder = get_embedder()
    # Rebuild index manually
    embedder.build_index(record_ids, texts, metadatas)
    
    # Run evaluation
    rec_hits = {1: 0, 5: 0}
    mrr_list = []
    
    for eval_row in eval_rows:
        rec_id, subject, complaint, part, tc_code, country, model = eval_row
        query_text = f"Incident involving {part} failure with trouble code {tc_code} in {country}"
        results = embedder.search_subset(query_text, all_ids, k=5, threshold=0.0)
        retrieved_ids = [res["record_id"] for res in results]
        
        rank = -1
        if rec_id in retrieved_ids:
            rank = retrieved_ids.index(rec_id) + 1
            
        for k in [1, 5]:
            if rank != -1 and rank <= k:
                rec_hits[k] += 1
        mrr = 1.0 / rank if rank != -1 else 0.0
        mrr_list.append(mrr)
        
    recall_1 = (rec_hits[1] / len(eval_rows)) * 100.0
    recall_5 = (rec_hits[5] / len(eval_rows)) * 100.0
    mean_mrr = np.mean(mrr_list)
    
    return recall_1, recall_5, mean_mrr

def main():
    print("Starting heuristic summary tuning (optimized)...", flush=True)
    for f in formulas:
        print(f"\nEvaluating Formula: {f['name']}", flush=True)
        r1, r5, mrr = evaluate_formula(f['func'])
        print(f"Results -> Recall@1: {r1:.2f}%, Recall@5: {r5:.2f}%, MRR@5: {mrr:.4f}", flush=True)

if __name__ == "__main__":
    main()
