import os
import json
import sqlite3
import numpy as np
import faiss
from core.paths import get_db_path, get_index_path, get_metadata_path

from dataclasses import dataclass, field
from typing import List

@dataclass
class SearchResult:
    record_id: int
    score: float
    rank: int

@dataclass
class ThresholdSearchResults:
    query: str
    threshold_used: float
    results: List[SearchResult] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.results)

    @property
    def ids(self) -> List[int]:
        return [r.record_id for r in self.results]

    @property
    def scores(self) -> List[float]:
        return [r.score for r in self.results]

    @property
    def is_empty(self) -> bool:
        return len(self.results) == 0

    @property
    def summary_line(self) -> str:
        if self.is_empty:
            return f"threshold={self.threshold_used:.2f} → 0 rows matched"
        scores = self.scores
        return f"threshold={self.threshold_used:.2f} → {self.count} rows matched (scores {min(scores):.3f}–{max(scores):.3f})"

class SemanticSearcher:
    DEFAULT_THRESHOLD_LADDER = (0.40, 0.50, 0.60, 0.70, 0.80, 0.90)

    def __init__(self, index, id_map: List[int], model, max_results: int = 20):
        self.index = index
        self.id_map = id_map
        self.model = model
        self.max_results = max_results

    def _db_ids_to_positions(self, db_ids: List[int]) -> List[int]:
        db_ids_set = set(db_ids)
        positions = [pos for pos, db_id in enumerate(self.id_map) if db_id in db_ids_set]
        return positions

    def search(self, query: str, threshold: float = 0.60, candidate_ids: List[int] = None) -> ThresholdSearchResults:
        # 1. Encode query with normalization
        query_embedding = self.model.encode([query], show_progress_bar=False, convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        query_vec = np.array(query_embedding[0], dtype=np.float32)

        # 2. Get FAISS positions
        if candidate_ids is not None:
            positions = self._db_ids_to_positions(candidate_ids)
        else:
            positions = list(range(len(self.id_map)))

        # 3. Handle empty positions
        if not positions:
            print(f"Warning: No valid candidate positions for query: {query}")
            return ThresholdSearchResults(query=query, threshold_used=threshold)

        # 4. Reconstruct candidate embeddings from index
        flat_index = faiss.downcast_index(self.index.index)
        candidate_vecs = []
        for pos in positions:
            vec = flat_index.reconstruct(pos)
            candidate_vecs.append(vec)
        candidate_vecs = np.vstack(candidate_vecs).astype(np.float32)

        # 5. Compute cosine similarity
        scores = np.dot(candidate_vecs, query_vec)

        # 6. Apply threshold mask
        mask = scores >= threshold
        passing_indices = np.where(mask)[0]

        if len(passing_indices) == 0:
            best_score = float(np.max(scores)) if len(scores) > 0 else 0.0
            print(f"No results passed threshold {threshold:.2f} for query: {query}. Best score was: {best_score:.3f}")
            return ThresholdSearchResults(query=query, threshold_used=threshold)

        passing_positions = [positions[idx] for idx in passing_indices]
        passing_scores = scores[passing_indices]

        # 7. Sort descending
        sorted_indices = np.argsort(-passing_scores)
        sorted_positions = [passing_positions[idx] for idx in sorted_indices]
        sorted_scores = [passing_scores[idx] for idx in sorted_indices]

        # 8. Slice to max results
        sliced_positions = sorted_positions[:self.max_results]
        sliced_scores = sorted_scores[:self.max_results]

        # 9. Build SearchResult objects
        results = []
        for rank, (pos, score) in enumerate(zip(sliced_positions, sliced_scores), 1):
            db_id = self.id_map[pos]
            results.append(SearchResult(record_id=db_id, score=float(score), rank=rank))

        print(f"Threshold search complete: {len(results)} rows matched threshold >= {threshold:.2f} (from {len(positions)} total candidates)")
        return ThresholdSearchResults(query=query, threshold_used=threshold, results=results)

    def search_with_auto_threshold(self, query: str, ladder=DEFAULT_THRESHOLD_LADDER, target_min: int = 3, target_max: int = 15, candidate_ids: List[int] = None) -> ThresholdSearchResults:
        best = None
        for threshold in ladder:
            res = self.search(query, threshold=threshold, candidate_ids=candidate_ids)
            if res.count == 0:
                break
            best = res
            if res.count <= target_max:
                break
        
        if best is not None:
            return best
        return ThresholdSearchResults(query=query, threshold_used=ladder[0])

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
            self.model = SentenceTransformer(self.model_name, device="cpu")
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
