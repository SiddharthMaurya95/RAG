import sqlite3
import datetime
import pandas as pd
import sys
from nlp.pipeline import NLPProcessor
from analytics.engine import AnalyticsEngine
from analytics.graph_selector import select_chart_type
from core.singletons import get_embedder, get_llm, get_db_connection
from core.cache import QueryCache
from core.paths import get_db_path
import faiss
from core.logger import get_logger
from core.custom_exception import CustomException
from ui.progress_tracker import ProgressTracker

logger = get_logger(__name__)

def _clean_df_for_streamlit(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitizes DataFrames to prevent PyArrow serialization crashes (e.g., mixed types in object cols)."""
    if df is None or df.empty:
        return df
    
    # Fill NA on object/string cols and force them to string to ensure pure types
    object_cols = df.select_dtypes(include=['object', 'string']).columns
    if len(object_cols) > 0:
        df[object_cols] = df[object_cols].fillna("")
        df[object_cols] = df[object_cols].astype(str)
        # Clean up any literal 'nan' strings that might have resulted from astype(str)
        df[object_cols] = df[object_cols].replace(["None", "none", "NaN", "nan", "NULL", "null", "NaT", "nat"], "")
    return df

class QueryRouter:
    def __init__(self, db_path="data/automotive.db"):
        self.db_path = get_db_path(db_path)
        self.nlp = NLPProcessor()
        self.analytics_engine = AnalyticsEngine(self.db_path)
        self.cache = QueryCache(self.db_path)
        
    def dispatch_query(self, query_text, user_id=0, override_intent=None, threshold=None, chat_history=None):
        """
        Main entry point for processing query.
        Returns a dict containing:
          'intent': the classified intent,
          'type': 'text_stream' | 'table_stream' | 'table_only' | 'report',
          'data': raw dataframe or formatted text (depends on type),
          'citations': list of source FTIR records (if SEARCH),
          'chart_type': plotly chart type (if visualization/analytics),
          'chart_title': plotly chart title
        """
        logger.info(f"QueryRouter dispatching query: '{query_text}' (user_id={user_id}, override_intent={override_intent})")
        # 1. Check Query Cache (L1/L2)
        is_explicit_override = override_intent not in (None, "ANALYTICS")
        if not is_explicit_override and threshold is None:
            cached_result = self.cache.get(query_text, user_id)
            if cached_result:
                logger.info(f"Cache HIT for query: '{query_text}'")
                return cached_result

        # 2. Parse Query using NLP Processor
        parsed_query = self.nlp.parse_query(query_text)
        
        # Apply intent override if specified
        if override_intent and override_intent != "ANALYTICS":
            intent = override_intent
            if intent in ("COMPARE", "VISUALIZE+EXPLAIN"):
                intent = "ANALYTICS"
            intent_score = 1.0
            parsed_query["intent"] = intent
            parsed_query["intent_score"] = intent_score
        else:
            intent = parsed_query["intent"]
            intent_score = parsed_query["intent_score"]
            
        # Ensure SEARCH is never selected unless override_intent is explicitly SEARCH
        if intent == "SEARCH" and override_intent != "SEARCH":
            intent = "ANALYTICS"
            parsed_query["intent"] = "ANALYTICS"
            
        # Check if the query references any database columns or entity types
        has_col_ref = False
        entities = parsed_query.get("entities", {})
        
        # Clean entities: remove common English 3-letter stop words from SALES_MODEL
        cleaned_sales_models = []
        stop_words = {"can", "you", "the", "one", "and", "for", "not", "any", "all", "get", "how", "who", "why", "has", "had", "was", "are", "but", "out", "now", "new", "top", "use", "way", "its", "our", "day", "few"}
        for sm in entities.get("SALES_MODEL", []):
            if sm.lower() not in stop_words:
                cleaned_sales_models.append(sm)
                
        has_actual_entities = False
        for k, v in entities.items():
            if k == "SALES_MODEL":
                if cleaned_sales_models:
                    has_actual_entities = True
            else:
                if v:
                    has_actual_entities = True
                    
        actual_filters = {k: v for k, v in parsed_query.get("filters", {}).items() if k != "limit"}
        if has_actual_entities:
            has_col_ref = True
        elif actual_filters:
            has_col_ref = True
        else:
            column_keywords = [
                "part", "component", "model", "vin", "dealer", "company", "country", "nation",
                "dtc", "code", "complaint", "repair", "quality", "rank", "milage", "mileage",
                "km", "time", "date", "year", "month", "incident", "status", "factory", "person",
                "investigator", "department", "dept", "judgement", "action", "sbpr", "ftir"
            ]
            q = query_text.lower()
            if any(kw in q for kw in column_keywords):
                has_col_ref = True

        parsed_query["has_col_ref"] = has_col_ref
            
        filters = parsed_query["filters"]
        entities = parsed_query["entities"]
        
        logger.info(f"Routed Query: '{query_text}' | Selected Intent: {intent} (has_col_ref={has_col_ref})")
        
        result = {
            "query": query_text,
            "intent": intent,
            "intent_score": intent_score,
            "has_col_ref": has_col_ref,
            "type": "text_stream",
            "data": None,
            "citations": [],
            "chart_type": None,
            "chart_title": None
        }

        # 3. Route based on Intent
        tracker = None
        try:
            logger.info(f"Routing query to handler for intent: {intent}")
            if intent == "SEARCH":
                tracker = ProgressTracker([
                    "Understanding Search Query",
                    "Executing SQL Prefilter",
                    "Loading Candidate Records",
                    "Generating Query Embedding",
                    "Performing Semantic Search",
                    "Computing Cosine Similarity",
                    "Filtering Relevant Records",
                    "Preparing Search Results",
                    "Displaying Results"
                ], title="Processing Search Request")
                tracker.start_stage("Understanding Search Query")
                tracker.complete_stage("Understanding Search Query")
                self._handle_search(parsed_query, result, threshold=threshold, chat_history=chat_history, tracker=tracker)
                
            elif intent == "ANALYTICS":
                tracker = ProgressTracker([
                    "Understanding Analytics Query",
                    "Generating SQL",
                    "Executing SQL",
                    "Loading Data",
                    "Computing KPIs",
                    "Generating Charts",
                    "Generating Report",
                    "Rendering Dashboard"
                ], title="Processing Analytics Request")
                tracker.start_stage("Understanding Analytics Query")
                tracker.complete_stage("Understanding Analytics Query")
                self._handle_analytics(parsed_query, result, tracker=tracker)
            
            logger.info("Query processing completed successfully.")
        except Exception as e:
            logger.error(f"Error during query execution: {e}")
            if tracker:
                tracker.fail_stage(tracker.stages[tracker.current_stage_idx] if tracker.current_stage_idx < len(tracker.stages) else "Execution", str(e))
            suggestion = self.suggest_corrected_query(query_text)
            if suggestion:
                result.update({
                    "type": "text_stream",
                    "data": [f"An error occurred while processing your request. Do you mean \"{suggestion}\"?"],
                    "citations": []
                })
            else:
                raise CustomException(e, sys)
            
        return result



    def suggest_corrected_query(self, query_text):
        """Uses the LLM to suggest a valid alternative query based on the database context."""
        schema_info = (
            "Actual SQLite Database Schema:\n"
            "- Table 'records': contains columns [id, ftir_no, product_model_code, sales_model_code, segmentation, vin, engine_no, transmission_no, reported_company, issued_company, outbreak_country, subject, customer_complaint, trouble_code_complaint, trouble_code_defect, checked_contents, checked_results, repair_status, repair_contents, problem_solved, causal_parts_no, causal_parts_name, quality, using_km_int, report_year, report_month, is_resolved]\n"
            "- Table 'mv_country_month': columns [outbreak_country, report_year, report_month, record_count]\n"
            "- Table 'mv_trouble_codes': columns [trouble_code, record_count]\n"
            "- Table 'mv_dealer_summary': columns [reported_company, record_count]\n"
            "- Table 'mv_quality_dist': columns [quality, record_count]\n"
        )
        system_prompt = (
            "You are an expert technical QA assistant. The user asked a query that returned no results, threw an error, or was not understood. "
            "Recommend a valid alternative query that matches the actual schema patterns in the database.\n"
            f"{schema_info}\n"
            "Rules:\n"
            "1. The suggested query MUST ALWAYS be written in user-friendly natural language (e.g. \"show all distinct countries\" or \"show the monthly failure trend\"). Do NOT output SQL syntax, SELECT statements, or database code blocks under any circumstances.\n"
            "2. Translate SQL queries into clean natural language questions that target valid database schemas.\n"
            "3. If they misspelled trouble codes (e.g. 'P030' instead of 'P0300'), correct it.\n"
            "4. Return ONLY the suggested query string inside double quotes (e.g. \"show all unique countries where incidents occurred\" or \"show the trend of DTC complaint codes in 2025\"). Do not output anything else."
        )
        prompt = (
            f"<|system|>\n{system_prompt}<|end|>\n"
            f"<|user|>\nFailed Query: {query_text}<|end|>\n"
            f"<|assistant|>\n"
        )
        try:
            from core.singletons import get_llm
            import re
            llm_client = get_llm()
            suggestion = llm_client.generate_summary(prompt, max_tokens=30).strip()
            # Extract content between double quotes if present
            match = re.search(r'"([^"]+)"', suggestion)
            if match:
                return match.group(1)
            return suggestion.replace('"', '')
        except Exception as e:
            print(f"Error suggesting corrected query: {e}")
            return None


    def _handle_search(self, parsed_query, result, threshold=None, chat_history=None, tracker=None):
        """Processes hybrid vector search: SQL pre-filter -> FAISS subset -> llm generation."""
        query_text = parsed_query["query"]
        
        from rag.retriever import Retriever
        # Pass self.nlp to avoid creating a second NLPProcessor with duplicate DB scans.
        retriever = Retriever(db_path=self.db_path, nlp=self.nlp)
        
        # Pass the already-computed parsed_query to avoid re-parsing the query a second time.
        retrieval_res = retriever.retrieve(query_text, threshold=threshold,
                                           parsed_query=parsed_query, tracker=tracker)
        
        if tracker:
            tracker.start_stage("Preparing Search Results")
        
        records = retrieval_res["records"]
        threshold_used = retrieval_res["threshold"]
        scores = retrieval_res["scores"]
        count = retrieval_res["count"]
        total_candidates = retrieval_res["total_candidates"]
        
        if count == 0:
            query_intent = result.get("intent", "SEARCH")
            has_col_ref = parsed_query.get("has_col_ref", True)
            
            if query_intent == "SEARCH" and has_col_ref:
                suggestion = self.suggest_corrected_query(query_text)
                if suggestion:
                    result.update({
                        "type": "text_stream",
                        "data": [f"No sufficiently similar technical incidents found (threshold={threshold_used:.2f}). Do you mean \"{suggestion}\"?"],
                        "citations": [],
                        "threshold_used": threshold_used,
                        "row_count": 0,
                        "score_range": "0.0 - 0.0",
                        "scores_list": []
                    })
                else:
                    result.update({
                        "type": "text_stream",
                        "data": [f"No sufficiently similar technical incidents found (threshold={threshold_used:.2f})."],
                        "citations": [],
                        "threshold_used": threshold_used,
                        "row_count": 0,
                        "score_range": "0.0 - 0.0",
                        "scores_list": []
                    })
            else:
                # Conversational follow-up (no column ref) OR general conversation:
                # Answer using LLM's own knowledge + conversation history!
                system_prompt = (
                    "You are a helpful automotive engineering assistant. Answer the user's question using your general knowledge "
                    "and the previous conversation history.\n\n"
                    "Rules:\n"
                    "1. If the user is asking to explain the previous query, the last query, or the SQL query shown above, "
                    "look at the conversation history and clearly explain what that query was doing and why.\n"
                    "2. Be technical, precise, and direct."
                )
                messages = [{"role": "system", "content": system_prompt}]
                if chat_history:
                    relevant_history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in chat_history
                        if m.get("role") in ("user", "assistant") and m.get("content")
                    ]
                    messages.extend(relevant_history[-8:])
                
                if tracker:
                    tracker.complete_stage("Preparing Search Results")
                    tracker.start_stage("Displaying Results")
                    tracker.complete_stage("Displaying Results")
                
                messages.append({"role": "user", "content": query_text})
                
                result.update({
                    "type": "text_stream",
                    "data": messages,
                    "citations": [],
                    "threshold_used": threshold_used,
                    "row_count": 0,
                    "score_range": "0.0 - 0.0",
                    "scores_list": []
                })
            return
            
        # Citations list
        citations = []
        for rec in records:
            citations.append({
                "ftir_no": rec["ftir_no"],
                "subject": rec["subject"],
                "reported_company": rec["reported_company"],
                "quality": rec["quality"],
                "outbreak_country": rec["outbreak_country"]
            })
            
        # Determine chart selection and run analytics SQL if needed FIRST
        chart_type = "empty"
        chart_title = None
        sql_query_used = None
        aggregated_df = None
        
        display_cols = list(retrieval_res["flagged_df"].columns)
        final_df = retrieval_res["flagged_df"][display_cols].copy()
        final_df = _clean_df_for_streamlit(final_df)
        
        try:
            from analytics.graph_selector import select_chart_type
            intent = parsed_query["intent"]
            chart_type, chart_title = select_chart_type(intent, final_df, query_text)
            
            # If a chart is requested in Search intent, run the analytics engine on the flagged rows!
            if chart_type != "empty":
                aggregated_df, sql_query_used = self.analytics_engine.query_via_llm(query_text, target_df=retrieval_res["flagged_df"])
                if aggregated_df is not None and not aggregated_df.empty:
                    aggregated_df = _clean_df_for_streamlit(aggregated_df)
                    chart_type, chart_title = select_chart_type(intent, aggregated_df, query_text) # Re-evaluate chart on aggregated df
        except Exception as e:
            logger.warning(f"Failed to run analytics on flagged_df: {e}")
            pass

        # Call the new InsightGenerator to produce Business Summary insights from the retrieved/aggregated dataframe
        from insight.generator import InsightGenerator
        insight_gen = InsightGenerator()
        
        # Use the SQL-generated/aggregated columns if available, otherwise fall back to search results
        insight_target_df = aggregated_df if (aggregated_df is not None and not aggregated_df.empty) else retrieval_res["flagged_df"]
        messages = insight_gen.generate_insight(query_text, insight_target_df)
        
        score_range = f"{min(scores):.3f} - {max(scores):.3f}" if scores else "0.000 - 0.000"
        
        result.update({
            "type": "table_stream",
            "data": {
                "df": final_df, # Keep original search results for the table
                "messages": messages
            },
            "citations": citations,
            "threshold_used": threshold_used,
            "row_count": count,
            "score_range": score_range,
            "scores_list": scores,
            "chart_type": chart_type,
            "chart_title": chart_title,
            "chart_data": aggregated_df,
            "sql_query": sql_query_used
        })

    def _handle_analytics(self, parsed_query, result, tracker=None):
        """Processes analytics metrics, groups data, selects Plotly format, and invokes LLM narration."""
        query_text = parsed_query["query"]
        intent = parsed_query["intent"]
        filters = parsed_query["filters"]
        entities = parsed_query["entities"]
        
        # Determine target of analytics
        q = query_text.lower()
        df = None
        sql_query_used = None
        
        # Try dynamic LLM SQL generation first
        try:
            df, sql_query_used = self.analytics_engine.query_via_llm(query_text, tracker=tracker)
            import logging
            logging.getLogger(__name__).info("Successfully executed LLM-generated SQL query from AnalyticsEngine.")
        except Exception as e:
            import logging
            import pandas as pd
            logging.getLogger(__name__).warning(f"LLM-generated SQL failed or was invalid: {e}")
            df = pd.DataFrame()
            sql_query_used = getattr(e, "failed_sql", None)

        # Clean out null/NaN/None/Unknown rows/cells from the DataFrame
        if not df.empty:
            if tracker:
                tracker.start_stage("Loading Data")
            df = df.dropna(how='all')
            if len(df.columns) > 0:
                first_col = df.columns[0]
                df = df.dropna(subset=[first_col])
                df = df[df[first_col].apply(lambda x: str(x).strip().lower() not in ('', 'none', 'nan', 'null', 'nat', 'unknown'))]
            
            df = _clean_df_for_streamlit(df)
            
            # Guardrail: Never expose VIN numbers
            for col in df.columns:
                if str(col).lower() in ("vin", "vin_no", "vin no", "vehicle identification number"):
                    df[col] = "********"

        if df.empty:
            suggestion = self.suggest_corrected_query(query_text)
            if suggestion:
                msg = f"No data available to analyze for the specified filters. Do you mean \"{suggestion}\"?"
            else:
                msg = "No data available to analyze for the specified filters."
            result.update({
                "type": "text_stream",
                "data": [msg]
            })
            if sql_query_used:
                result["sql_query"] = sql_query_used
            return

        if tracker:
            tracker.complete_stage("Loading Data")
            tracker.add_metric("Rows returned", len(df))
            tracker.start_stage("Computing KPIs")
            tracker.complete_stage("Computing KPIs")
            tracker.start_stage("Generating Charts")

        # Select Plotly chart type dynamically
        from analytics.graph_selector import select_chart_type
        chart_type, chart_title = select_chart_type(intent, df, query_text)
            
        # Call the new InsightGenerator
        from insight.generator import InsightGenerator
        insight_gen = InsightGenerator()
        final_insights = insight_gen.generate_insight(query_text, df)
        
        result.update({
            "type": "table_stream",
            "data": {
                "df": df,
                "messages": final_insights  # passed as string directly to frontend
            },
            "chart_type": chart_type,
            "chart_title": chart_title
        })
        if sql_query_used:
            result["sql_query"] = sql_query_used
        
        if tracker:
            tracker.complete_stage("Generating Charts")
            tracker.start_stage("Rendering Dashboard")
            tracker.complete_stage("Rendering Dashboard")
