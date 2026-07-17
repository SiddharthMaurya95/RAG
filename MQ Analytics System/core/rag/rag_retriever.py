# =====================================================
# ✅ HYBRID RETRIEVER
# =====================================================
import sqlite3
import pandas as pd
import numpy as np
import os
from typing import List

from core.rag.embedding_service import EmbeddingService
from core.rag.similarity import compute_cosine_similarity
from core.paths import get_db_path, get_project_root

from core.utils.decorators import with_logging_and_exceptions

class Retriever:
    THRESHOLD_LADDER = (0.40, 0.50, 0.60, 0.70, 0.80, 0.90)

    def __init__(self, db_path="data/automotive.db", nlp=None):
        self.db_path = get_db_path(db_path)
        if nlp is not None:
            self.nlp = nlp
        else:
            from core.nlp.pipeline import NLPProcessor
            self.nlp = NLPProcessor()
            
        cache_dir = os.path.join(get_project_root(), "data")
        self.embedding_service = EmbeddingService(cache_dir=cache_dir)
        # Ensure embeddings are loaded into memory
        self.embedding_service.load_embeddings()

    def _auto_threshold_search(self, candidate_embeddings: np.ndarray, query_embedding: np.ndarray, target_max: int = 15):
        best_similarities = np.array([])
        best_threshold = self.THRESHOLD_LADDER[0]
        
        # Calculate raw similarities once
        similarities = compute_cosine_similarity(query_embedding, candidate_embeddings)
        
        for thresh in self.THRESHOLD_LADDER:
            mask = similarities >= thresh
            count = np.sum(mask)
            if count == 0:
                break
            best_similarities = similarities
            best_threshold = thresh
            if count <= target_max:
                break
                
        if len(best_similarities) == 0:
            return similarities, self.THRESHOLD_LADDER[0]
        return best_similarities, best_threshold

    @with_logging_and_exceptions
    def retrieve(self, query: str, threshold: float | None = None,
                 parsed_query: dict | None = None, tracker=None) -> dict:
        """
        Retrieves matching records using hybrid SQL pre-filtering + Pandas/NumPy Semantic search.
        """
        if tracker:
            tracker.start_stage("Executing SQL Prefilter")
        # 1. SQL pre-filtering to get candidate_ids
        if parsed_query is None:
            parsed_query = self.nlp.parse_query(query)
        entities = parsed_query["entities"]
        filters = parsed_query["filters"]
        
        has_filters = (
            entities["TROUBLE_CODE"] or entities["PRODUCT_MODEL"] or entities["COUNTRY"] or
            filters.get("segmentation") or filters.get("quality") or filters.get("km_max") or filters.get("km_min")
        )
        
        candidate_ids = None
        if has_filters:
            from core.database import get_session, Record
            session = get_session(self.db_path)
            try:
                query_obj = session.query(Record.id)
                if entities["TROUBLE_CODE"]:
                    query_obj = query_obj.filter(Record.trouble_code_complaint.ilike(entities["TROUBLE_CODE"][0]))
                if entities["PRODUCT_MODEL"]:
                    query_obj = query_obj.filter(Record.product_model_code.ilike(entities["PRODUCT_MODEL"][0]))
                if entities["COUNTRY"]:
                    query_obj = query_obj.filter(Record.outbreak_country.ilike(entities["COUNTRY"][0]))
                if filters.get("segmentation"):
                    query_obj = query_obj.filter(Record.segmentation.ilike(filters["segmentation"]))
                if filters.get("quality"):
                    query_obj = query_obj.filter(Record.quality.ilike(filters["quality"]))
                if filters.get("km_max"):
                    query_obj = query_obj.filter(Record.using_km_int > 0, Record.using_km_int < filters["km_max"])
                if filters.get("km_min"):
                    query_obj = query_obj.filter(Record.using_km_int > filters["km_min"])
                    
                candidate_ids = [r[0] for r in query_obj.all()]
            finally:
                session.close()
                
            if not candidate_ids:
                candidate_ids = None
                
        if tracker:
            tracker.complete_stage("Executing SQL Prefilter")
            if candidate_ids:
                tracker.add_metric("Candidate records", len(candidate_ids))
                tracker.stage_info["Executing SQL Prefilter"] = f"{len(candidate_ids):,} candidate records"
            tracker.start_stage("Loading Candidate Records")
                
        # 2. Load SQL result into a Pandas DataFrame
        conn = sqlite3.connect(self.db_path)
        if candidate_ids is not None:
            placeholders = ",".join(["?"] * len(candidate_ids))
            sql = f"SELECT * FROM records WHERE id IN ({placeholders})"
            df = pd.read_sql_query(sql, conn, params=candidate_ids)
        else:
            df = pd.read_sql_query("SELECT * FROM records", conn)
        conn.close()

        total_candidates = len(df)
        
        if df.empty:
            return {
                "flagged_df": pd.DataFrame(),
                "records": [],
                "threshold": threshold if threshold else self.THRESHOLD_LADDER[0],
                "scores": [],
                "count": 0,
                "total_candidates": 0
            }

        if tracker:
            tracker.complete_stage("Loading Candidate Records")
            tracker.start_stage("Generating Query Embedding")

        # 3. Get candidate embeddings
        all_embeddings, all_ids = self.embedding_service.get_embeddings()
        
        if all_embeddings is None or len(all_embeddings) == 0:
            print("Embeddings not loaded or generated yet. Please run offline preprocessing.")
            return {
                "flagged_df": pd.DataFrame(),
                "records": [],
                "threshold": threshold if threshold else self.THRESHOLD_LADDER[0],
                "scores": [],
                "count": 0,
                "total_candidates": total_candidates
            }

        # Map candidate IDs to embedding matrix indices
        id_to_idx = {fid: idx for idx, fid in enumerate(all_ids)}
        
        # Filter dataframe rows that have embeddings
        df['emb_idx'] = df['id'].map(id_to_idx)
        df_valid = df.dropna(subset=['emb_idx']).copy()
        
        if df_valid.empty:
            return {
                "flagged_df": pd.DataFrame(),
                "records": [],
                "threshold": threshold if threshold else self.THRESHOLD_LADDER[0],
                "scores": [],
                "count": 0,
                "total_candidates": total_candidates
            }
            
        candidate_indices = df_valid['emb_idx'].astype(int).tolist()
        candidate_embeddings = all_embeddings[candidate_indices]

        # 4. Generate ONE embedding for the user's Search query
        query_embedding = self.embedding_service.encode(query)

        if tracker:
            tracker.complete_stage("Generating Query Embedding")
            tracker.start_stage("Performing Semantic Search")
            tracker.complete_stage("Performing Semantic Search") # Fast operation
            tracker.start_stage("Computing Cosine Similarity")

        # 5. Compute cosine similarity
        if threshold is not None:
            similarities = compute_cosine_similarity(query_embedding, candidate_embeddings)
            threshold_used = threshold
        else:
            similarities, threshold_used = self._auto_threshold_search(
                candidate_embeddings, query_embedding, target_max=15
            )

        if tracker:
            tracker.complete_stage("Computing Cosine Similarity")
            tracker.start_stage("Filtering Relevant Records")

        # 6. Create temporary DataFrame columns
        df_valid['similarity'] = similarities
        df_valid['flag'] = df_valid['similarity'] >= threshold_used
        
        # Filter and sort
        flagged_df = df_valid[df_valid['flag']].copy()
        flagged_df = flagged_df.sort_values(by='similarity', ascending=False)
        
        # Drop temporary indexing column
        flagged_df = flagged_df.drop(columns=['emb_idx'])
        
        # Prepare list of dictionaries for legacy compatibility if needed
        records_list = flagged_df.to_dict(orient="records")
        sorted_scores = flagged_df['similarity'].tolist()
        count = len(flagged_df)

        if tracker:
            tracker.complete_stage("Filtering Relevant Records")
            tracker.add_metric("Similarity threshold", f"{threshold_used:.2f}")
            tracker.add_metric("Relevant records", count)
            tracker.add_metric("Rows returned", count)
            tracker.stage_info["Filtering Relevant Records"] = f"Matched Records: {count:,} (Threshold: {threshold_used:.2f})"

        return {
            "flagged_df": flagged_df,
            "records": records_list,
            "threshold": threshold_used,
            "scores": sorted_scores,
            "count": count,
            "total_candidates": total_candidates
        }
