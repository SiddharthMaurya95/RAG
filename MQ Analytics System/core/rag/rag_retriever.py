import sqlite3
import pandas as pd
import numpy as np
import faiss
from typing import List

class Retriever:
    THRESHOLD_LADDER = (0.40, 0.50, 0.60, 0.70, 0.80, 0.90)

    def __init__(self, db_path="data/automotive.db", nlp=None):
        from core.paths import get_db_path
        self.db_path = get_db_path(db_path)
        if nlp is not None:
            # Reuse a pre-built NLPProcessor to avoid redundant DB scans
            self.nlp = nlp
        else:
            from core.engine.intent.nlp import NLPProcessor
            self.nlp = NLPProcessor()

    def retrieve(self, query: str, threshold: float | None = None, max_results: int = 15,
                 parsed_query: dict | None = None) -> dict:
        """
        Retrieves matching records using hybrid SQL pre-filtering + FAISS Semantic search
        with custom cosine similarity thresholding.

        Args:
            parsed_query: Pre-computed result from nlp.parse_query(). If provided, the
                          NLP parse step is skipped to avoid redundant computation.
        """
        # 1. SQL pre-filtering to get candidate_ids
        # Reuse pre-parsed query from caller if available to avoid duplicate NLP work
        if parsed_query is None:
            parsed_query = self.nlp.parse_query(query)
        entities = parsed_query["entities"]
        filters = parsed_query["filters"]
        
        # Only hit the database for IDs when there are active filter conditions.
        # For unfiltered queries, pass candidate_ids=None so FAISS searches the
        # full index without a pre-filter, eliminating the full-table id scan.
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
                
            # If strict filter yielded no results, fall back to full-index FAISS search
            if not candidate_ids:
                candidate_ids = None

        # Instantiate SemanticSearcher
        from core.singletons import get_embedder
        embedder = get_embedder()
        
        # Load FAISS index if not loaded
        if embedder.index is None:
            embedder.load_index()
            
        # Get id_map from index
        id_map = faiss.vector_to_array(embedder.index.id_map).tolist()
        
        from rag.embedder import SemanticSearcher
        searcher = SemanticSearcher(embedder.index, id_map, embedder.model, max_results=max_results)
        
        # 2. Call search or search_with_auto_threshold
        if threshold is not None:
            search_result = searcher.search(query, threshold=threshold, candidate_ids=candidate_ids)
        else:
            search_result = searcher.search_with_auto_threshold(
                query, 
                ladder=self.THRESHOLD_LADDER, 
                target_min=3, 
                target_max=15, 
                candidate_ids=candidate_ids
            )
            
        # 3. If empty results
        n_candidates = len(candidate_ids) if candidate_ids is not None else embedder.index.ntotal
        if search_result.is_empty:
            return {
                "records": [],
                "threshold": search_result.threshold_used,
                "scores": [],
                "count": 0,
                "total_candidates": n_candidates
            }
            
        # 4. Fetch full database rows
        from core.database import get_session, Record
        session = get_session(self.db_path)
        try:
            records_query = session.query(
                Record.id, Record.ftir_no, Record.subject, Record.quality, Record.outbreak_country,
                Record.reported_company, Record.trouble_code_complaint, Record.customer_complaint,
                Record.checked_contents, Record.checked_results, Record.repair_contents, Record.causal_parts_name,
                Record.summary, Record.product_model_code
            ).filter(Record.id.in_(search_result.ids)).all()
            
            columns = ['id', 'ftir_no', 'subject', 'quality', 'outbreak_country', 
                       'reported_company', 'trouble_code_complaint', 'customer_complaint', 
                       'checked_contents', 'checked_results', 'repair_contents', 'causal_parts_name', 'summary', 'product_model_code']
            df_matches = pd.DataFrame(records_query, columns=columns)
        finally:
            session.close()
        
        # 5. Sort fetched records to match score order
        score_map = {r.record_id: r.score for r in search_result.results}
        
        records_list = df_matches.to_dict(orient="records")
        records_list = sorted(records_list, key=lambda x: score_map.get(x["id"], 0.0), reverse=True)
        
        sorted_scores = [score_map.get(rec["id"], 0.0) for rec in records_list]
        
        return {
            "records": records_list,
            "threshold": search_result.threshold_used,
            "scores": sorted_scores,
            "count": len(records_list),
            "total_candidates": n_candidates
        }
