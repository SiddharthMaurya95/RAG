import sqlite3
import datetime
import pandas as pd
from nlp.pipeline import NLPProcessor
from analytics.engine import AnalyticsEngine
from analytics.graph_selector import select_chart_type
from core.singletons import get_embedder, get_llm, get_db_connection
from core.cache import QueryCache
from core.paths import get_db_path
import faiss

class QueryRouter:
    def __init__(self, db_path="data/automotive.db"):
        self.db_path = get_db_path(db_path)
        self.nlp = NLPProcessor()
        self.analytics_engine = AnalyticsEngine(self.db_path)
        self.cache = QueryCache(self.db_path)
        
    def dispatch_query(self, query_text, user_id=0):
        """
        Main entry point for processing query.
        Returns a dict containing:
          'intent': the classified intent,
          'type': 'text_stream' | 'table_stream' | 'table_only' | 'report' | 'escalation',
          'data': raw dataframe or formatted text (depends on type),
          'citations': list of source FTIR records (if SEARCH),
          'chart_type': plotly chart type (if visualization/analytics),
          'chart_title': plotly chart title
        """
        # 1. Check Query Cache (L1/L2)
        cached_result = self.cache.get(query_text, user_id)
        if cached_result:
            print(f"Cache HIT for query: {query_text}")
            return cached_result

        # 2. Parse Query using NLP Processor
        parsed_query = self.nlp.parse_query(query_text)
        intent = parsed_query["intent"]
        intent_score = parsed_query["intent_score"]
        filters = parsed_query["filters"]
        entities = parsed_query["entities"]
        
        print(f"Routed Query: '{query_text}' | Intent: {intent}")
        
        result = {
            "query": query_text,
            "intent": intent,
            "intent_score": intent_score,
            "type": "text_stream",
            "data": None,
            "citations": [],
            "chart_type": None,
            "chart_title": None
        }

        # 3. Route based on Intent
        if intent == "SEARCH" or intent == "AMBIGUOUS":
            self._handle_search(parsed_query, result)
            
        elif intent in ("ANALYTICS", "VISUALIZE", "VISUALIZE+EXPLAIN", "COMPARE"):
            self._handle_analytics(parsed_query, result)
            

        elif intent == "REPORT":
            result.update({
                "type": "report",
                "data": {
                    "year": filters.get("year", datetime.datetime.now().year),
                    "month": filters.get("month", datetime.datetime.now().month)
                }
            })
            
        return result

    def _handle_search(self, parsed_query, result):
        """Processes hybrid vector search: SQL pre-filter -> FAISS subset -> llm generation."""
        query_text = parsed_query["query"]
        entities = parsed_query["entities"]
        filters = parsed_query["filters"]
        
        # Build SQL dynamic WHERE clause based on NLP entities
        where_clauses = []
        params = []
        
        if entities["TROUBLE_CODE"]:
            where_clauses.append("LOWER(trouble_code_complaint) = LOWER(?)")
            params.append(entities["TROUBLE_CODE"][0])
        if entities["PRODUCT_MODEL"]:
            where_clauses.append("LOWER(product_model_code) = LOWER(?)")
            params.append(entities["PRODUCT_MODEL"][0])
        if entities["COUNTRY"]:
            where_clauses.append("LOWER(outbreak_country) = LOWER(?)")
            params.append(entities["COUNTRY"][0])
        if filters.get("segmentation"):
            where_clauses.append("LOWER(segmentation) = LOWER(?)")
            params.append(filters["segmentation"])
        if filters.get("quality"):
            where_clauses.append("LOWER(quality) = LOWER(?)")
            params.append(filters["quality"])
        if filters.get("km_max"):
            where_clauses.append("using_km_int > 0 AND using_km_int < ?")
            params.append(filters["km_max"])
        if filters.get("km_min"):
            where_clauses.append("using_km_int > ?")
            params.append(filters["km_min"])
            
        # Get keywords
        keywords = self.nlp.extract_keywords(query_text)
        
        # SQL Pre-filter execution to get metadata whitelist
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if where_clauses:
            sql_query = f"SELECT id FROM records WHERE {' AND '.join(where_clauses)}"
            cursor.execute(sql_query, params)
            metadata_whitelisted_ids = [row[0] for row in cursor.fetchall()]
            
            # If strict filter yielded no results, fall back to all records
            if not metadata_whitelisted_ids:
                cursor.execute("SELECT id FROM records")
                metadata_whitelisted_ids = [row[0] for row in cursor.fetchall()]
        else:
            cursor.execute("SELECT id FROM records")
            metadata_whitelisted_ids = [row[0] for row in cursor.fetchall()]
            
        # 1. Search SQL first using keyword LIKE query
        sql_matched_ids = []
        if keywords:
            kw_clauses = []
            kw_params = []
            for kw in keywords:
                kw_clauses.append("(LOWER(subject) LIKE ? OR LOWER(customer_complaint) LIKE ? OR LOWER(causal_parts_name) LIKE ? OR LOWER(summary) LIKE ?)")
                kw_params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%", f"%{kw}%"])
            
            kw_query = f"SELECT id FROM records WHERE {' OR '.join(kw_clauses)}"
            cursor.execute(kw_query, kw_params)
            db_matched_ids = [row[0] for row in cursor.fetchall()]
            sql_matched_ids = list(set(metadata_whitelisted_ids).intersection(set(db_matched_ids)))
            
        conn.close()

        # 2. Search vector datastore using FAISS with a dynamic threshold
        # If we found keyword matches, we can be more lenient (threshold 0.30)
        # If no keywords matched, we use a strict threshold (0.45) to filter out unrelated queries.
        search_threshold = 0.30 if sql_matched_ids else 0.45
        embedder = get_embedder()
        faiss_results = embedder.search_subset(query_text, metadata_whitelisted_ids, k=None, threshold=search_threshold)
        
        # 3. Determine if the query is related to the subject of FTIR
        is_related = bool(sql_matched_ids) or bool(faiss_results)
        
        if not is_related:
            # Fall back to general assistant
            system_prompt = (
                "You are a helpful and knowledgeable assistant. "
                "Answer the user's question directly, accurately, and politely based on your general knowledge. "
                "Keep your response concise and helpful."
            )
            prompt = f"User Question: {query_text}\nAnswer:"
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            result.update({
                "type": "text_stream",
                "data": messages,
                "citations": []
            })
            return
            
        # Combine SQL matches and FAISS results, prioritizing FAISS scores
        combined_dict = {}
        for r in faiss_results:
            combined_dict[r["record_id"]] = r["score"]
        # Include SQL keyword matches that weren't caught by the vector search threshold
        for rid in sql_matched_ids:
            if rid not in combined_dict:
                combined_dict[rid] = 0.35  # Assign baseline score
                
        # Sort combined results by score descending
        combined_results = sorted(
            [{"record_id": rid, "score": score} for rid, score in combined_dict.items()],
            key=lambda x: x["score"],
            reverse=True
        )
        
        # Get total matching count
        total_count = len(combined_results)
        
        # Limit to top 5 for the LLM prompt summaries and citations
        top_results = combined_results[:5]
        matched_ids = [r["record_id"] for r in top_results]
        
        conn = sqlite3.connect(self.db_path)
        # Use pandas to load matched rows cleanly
        placeholders = ','.join('?' for _ in matched_ids)
        query = f"""
            SELECT id, ftir_no, subject, quality, outbreak_country, 
                   reported_company, trouble_code_complaint, summary 
            FROM records 
            WHERE id IN ({placeholders});
        """
        df_matches = pd.read_sql_query(query, conn, params=matched_ids)
        conn.close()
        
        # Sort dataframe to match FAISS scoring order
        df_matches['sort_order'] = df_matches['id'].apply(lambda x: matched_ids.index(x))
        df_matches = df_matches.sort_values('sort_order').drop(columns=['sort_order'])
        
        # Citations list
        citations = df_matches[['ftir_no', 'subject', 'reported_company', 'quality', 'outbreak_country']].to_dict(orient='records')
        
        # Formulate LLM Prompt using precomputed summaries
        summaries_text = []
        for i, row in enumerate(df_matches.itertuples(), 1):
            summaries_text.append(f"Case {i} (FTIR {row.ftir_no}): {row.summary}")
            
        context = "\n".join(summaries_text)
        
        system_prompt = (
            "You are an expert automotive quality engineering assistant. "
            f"A semantic search for the user's specific query ('{query_text}') matched exactly {total_count} cases in our database. "
            "Below we provide only the top 5 most relevant sample cases for reference. "
            f"If the user asks for the total count, total number, or how many reports/cases exist for this query, you MUST answer that there are exactly {total_count} matching cases. "
            f"The count of {total_count} is the exact count of cases matching the query, so do not say it includes unrelated cases. Do not count the sample cases shown below."
        )
        
        prompt = (
            f"Historical QA cases context (showing top 5 most relevant sample cases out of {total_count} total matches in the database):\n{context}\n\n"
            f"User Question: {query_text}\n"
            f"Answer:"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # We pass a generator function (stream) or instructions
        result.update({
            "type": "text_stream",
            "data": messages,
            "citations": citations
        })

    def _handle_analytics(self, parsed_query, result):
        """Processes analytics metrics, groups data, selects Plotly format, and invokes LLM narration."""
        query_text = parsed_query["query"]
        intent = parsed_query["intent"]
        filters = parsed_query["filters"]
        entities = parsed_query["entities"]
        
        # Determine target of analytics
        q = query_text.lower()
        df = pd.DataFrame()
        sql_query_used = None
        
        # Try dynamic LLM SQL generation first
        try:
            df, sql_query_used = self.analytics_engine.query_via_llm(query_text)
            print("Successfully executed LLM-generated SQL query.")
        except Exception as e:
            print(f"LLM-generated SQL failed or was invalid, falling back to static router: {e}")
            df = pd.DataFrame()
            
        if df.empty:
            model = entities["PRODUCT_MODEL"][0] if entities["PRODUCT_MODEL"] else None
            segment = filters.get("segmentation")
            
            # Route to correct AnalyticsEngine function
            if "dealer" in q or "company" in q:
                df, sql_query_used = self.analytics_engine.get_top_dealers_or_countries("dealer", limit=filters.get("limit", 10), country=entities["COUNTRY"][0] if entities["COUNTRY"] else None)
            elif "country" in q or "nation" in q:
                df, sql_query_used = self.analytics_engine.get_top_dealers_or_countries("country", limit=filters.get("limit", 10))
            elif "trouble" in q or "dtc" in q or "code" in q:
                df, sql_query_used = self.analytics_engine.get_trouble_code_frequency(limit=filters.get("limit", 10), model=model, segmentation=segment)
            elif "trend" in q or "month" in q or "time" in q:
                df, sql_query_used = self.analytics_engine.get_monthly_failure_trend(year=filters.get("year"), model=model)
            elif "compare" in q or "versus" in q or "vs" in q:
                df, sql_query_used = self.analytics_engine.get_model_comparison()
            elif "mileage" in q or "km" in q:
                df, sql_query_used = self.analytics_engine.get_using_km_distribution(model=model)
            elif "quality" in q:
                df, sql_query_used = self.analytics_engine.get_quality_distribution(model=model)
            elif "success" in q or "resolution" in q or "solved" in q:
                if "total" in q or "overall" in q or "global" in q:
                    df, sql_query_used = self.analytics_engine.get_overall_resolution_stats()
                else:
                    df, sql_query_used = self.analytics_engine.get_repair_success_rate()
            elif "part" in q or "component" in q or "causal" in q:
                df, sql_query_used = self.analytics_engine.get_failed_parts_frequency(limit=filters.get("limit", 10), model=model, segmentation=segment)
            else:
                # Default fallback: Model comparison
                df, sql_query_used = self.analytics_engine.get_model_comparison()

        if df.empty:
            result.update({
                "type": "text_stream",
                "data": ["No data available to analyze for the specified filters."]
            })
            return

        # Select Plotly chart type dynamically
        chart_type, chart_title = select_chart_type(intent, df, query_text)
            
        # Compile Markdown representation for LLM narration (preventing context window overflow)
        if len(df) > 20:
            if "mileage" in df.columns or "km" in df.columns or (len(df.columns) == 1 and df.columns[0] == "mileage"):
                # For large mileage lists (e.g. histograms), describe the statistics instead of dumping raw rows
                markdown_table = df.describe().to_markdown()
            else:
                # Cap standard tables to top 20 rows
                markdown_table = df.head(20).to_markdown(index=False) + f"\n\n*(Table truncated to top 20 of {len(df)} rows)*"
        else:
            markdown_table = df.to_markdown(index=False)
        
        system_prompt = (
            "You are an expert automotive quality engineering analyst. Explain the highlights, trends, or insights of the "
            "provided FTIR (Fourier Transform Infrared Spectroscopy) data table to answer the user's specific query. "
            "Focus on numerical counts, differences, and maximums, providing the appropriate context of the query and the FTIR records. "
            "Keep your response concise and professional (2-3 sentences)."
        )
        
        prompt = (
            f"User Query: {query_text}\n"
            f"SQL Query Executed: {sql_query_used if sql_query_used else 'N/A'}\n\n"
            f"FTIR Data Table:\n{markdown_table}\n\n"
            f"Analysis and Answer:"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        result.update({
            "type": "table_stream",
            "data": {
                "df": df,
                "messages": messages
            },
            "chart_type": chart_type,
            "chart_title": chart_title
        })
        if sql_query_used:
            result["sql_query"] = sql_query_used
