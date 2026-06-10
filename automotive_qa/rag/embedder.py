import os
import json
import sqlite3
import numpy as np
import faiss
from core.paths import get_db_path, get_index_path, get_metadata_path

class VectorEmbedder:
    def __init__(self, model_name="all-MiniLM-L6-v2", index_path="data/faiss_index.bin", metadata_path="data/vector_metadata.json"):
        self.model_name = model_name
        self.index_path = get_index_path(index_path)
        self.metadata_path = get_metadata_path(metadata_path)
        self.model = None
        self.index = None
        self.metadata = [] # List of dicts matching FAISS index row-by-row
        
    def load_model(self):
        """Loads the SentenceTransformer model into memory."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        return self.model

    def encode(self, texts):
        """Generates embeddings for a list of texts. Returns normalized numpy arrays."""
        self.load_model()
        
        from core.cache import EmbeddingCache
        emb_cache = EmbeddingCache()
        
        embeddings = []
        texts_to_encode = []
        indices_to_encode = []
        
        for idx, text in enumerate(texts):
            cached = emb_cache.get(text)
            if cached is not None:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                texts_to_encode.append(text)
                indices_to_encode.append(idx)
                
        if texts_to_encode:
            encoded = self.model.encode(texts_to_encode, show_progress_bar=False, convert_to_numpy=True)
            faiss.normalize_L2(encoded)
            for idx, text, emb in zip(indices_to_encode, texts_to_encode, encoded):
                try:
                    emb_cache.set(text, emb)
                except Exception as e:
                    print(f"Error saving embedding: {e}")
                embeddings[idx] = emb
                
        return np.array(embeddings, dtype=np.float32)

    def build_index(self, record_ids, texts, metadatas, nlist=100):
        """
        Builds the FAISS Flat IndexIDMap on the provided dataset.
        """
        dimension = 384 # MiniLM embedding size
        embeddings = self.encode(texts)
        
        print(f"Building FAISS Flat IndexIDMap with {len(embeddings)} vectors...")
        
        index_flat = faiss.IndexFlatIP(dimension)
        self.index = faiss.IndexIDMap(index_flat)
        
        # Add vectors with custom IDs matching the record IDs in SQLite
        record_ids_arr = np.array(record_ids, dtype=np.int64)
        self.index.add_with_ids(embeddings, record_ids_arr)
        
        self.metadata = metadatas
        self.save_index()
        print("FAISS IndexIDMap built and saved.")

    def append_to_index(self, record_ids, texts, metadatas):
        """Appends new vectors to the existing FAISS index incrementally."""
        if self.index is None:
            self.load_index()
            
        if self.index is None:
            # Build new index if none exists
            self.build_index(record_ids, texts, metadatas)
            return
            
        print(f"Appending {len(record_ids)} new vectors to FAISS index...")
        embeddings = self.encode(texts)
        record_ids_arr = np.array(record_ids, dtype=np.int64)
        
        self.index.add_with_ids(embeddings, record_ids_arr)
        self.metadata.extend(metadatas)
        self.save_index()
        print("FAISS index updated and saved.")

    def save_index(self):
        """Saves the FAISS index and parallel metadata list to disk."""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, 'w') as f:
            json.dump(self.metadata, f)

    def rebuild_index_from_db(self):
        """Rebuilds the FAISS IndexIDMap from the SQLite database records."""
        db_path = get_db_path("data/automotive.db")
        if not os.path.exists(db_path):
            print(f"Database not found at {db_path}, cannot rebuild index.")
            return
            
        import sqlite3
        from rag.document_builder import build_document_text
        
        print("Rebuilding FAISS index from database records...")
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
            
            metadatas.append({
                'id': rec_id,
                'country': row[7],
                'model': row[8],
                'trouble_code': row[9],
                'segment': row[10]
            })
            
        self.build_index(record_ids, texts, metadatas)

    def load_index(self):
        """Loads the FAISS index and metadata list from disk."""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            # Rebuild if not IndexIDMap
            if "IndexIDMap" not in str(type(self.index)):
                print("Loaded index is not IndexIDMap. Rebuilding from database...")
                self.rebuild_index_from_db()
            with open(self.metadata_path, 'r') as f:
                self.metadata = json.load(f)
            print("FAISS index and metadata loaded successfully.")
            return True
        else:
            print("FAISS index or metadata files do not exist on disk.")
            return False

    def search_subset(self, query_text, whitelisted_ids, k=None, nprobe=20, threshold=0.30):
        """
        Searches the FAISS index using a query embedding, restricted to a whitelist of IDs,
        using range_search to filter out low-similarity records (similarity < threshold).
        """
        if self.index is None:
            loaded = self.load_index()
            if not loaded:
                return []
                
        if not whitelisted_ids:
            return []
            
        # Get query embedding
        query_embedding = self.encode([query_text])
        
        # Build FAISS ID Selector for the whitelisted IDs
        whitelisted_ids_arr = np.array(whitelisted_ids, dtype=np.int64)
        id_selector = faiss.IDSelectorArray(whitelisted_ids_arr)
        
        # Prepare Search Parameters with the selector
        params = faiss.SearchParameters(sel=id_selector)
        
        # Perform range search
        lims, scores, indices = self.index.range_search(query_embedding, threshold, params=params)
        
        # Format results
        results = []
        if len(lims) > 1:
            start, end = lims[0], lims[1]
            for idx, score in zip(indices[start:end], scores[start:end]):
                if idx != -1:
                    results.append({
                        'record_id': int(idx),
                        'score': float(score)
                    })
                    
        # Sort by score in descending order
        results = sorted(results, key=lambda x: x['score'], reverse=True)
        
        # Limit to top k if specified
        if k is not None:
            return results[:k]
        return results
