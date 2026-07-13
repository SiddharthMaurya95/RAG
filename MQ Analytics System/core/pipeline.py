# =====================================================
# ✅ MAIN EXECUTION PIPELINE & ROUTER
# =====================================================
import pandas as pd
import datetime
import os

# Agents
from core.agents.code_agent import generate_code
from core.agents.debug_agent import fix_code
from core.agents.insight_agent import generate_insights
from core.agents.summary_agent import summarize
from core.agents.visualization_agent import VisualizationAgent

# Engine
from core.engine.validator import ensure_result_assignment
from core.engine.executor import CodeExecutor
from core.engine.intent.intent_classifier import Intent_classification
from core.engine.intent.nlp import NLPProcessor

# SQL
from core.sql.sql_agent import generate_sql
from core.sql.sql_executor import execute_sql, AnalyticsEngine
from core.utils.charts import apply_premium_layout

# Memory / Cache
from core.memory.chat_memory import ChatMemory
from core.cache import QueryCache
from core.singletons import get_embedder, get_llm

# Init globals
memory = ChatMemory()
executor = CodeExecutor()
intent_engine = Intent_classification()
visualizer = VisualizationAgent()


class QueryRouter:
    def __init__(self, db_path=None):
        if db_path is None:
            from core.config import DB_PATH
            db_path = DB_PATH
        self.db_path = db_path
        self.nlp = NLPProcessor()
        self.analytics_engine = AnalyticsEngine(self.db_path)
        self.cache = QueryCache(self.db_path)

    def dispatch_query(self, query_text, user_id=0, override_intent=None, threshold=None, max_results=15):
        """Main routing entry point for RAG, Analytics, and Report generation."""
        is_explicit_override = override_intent not in (None, "Auto (NLP Pipeline)")
        if not is_explicit_override and threshold is None:
            cached_result = self.cache.get(query_text, user_id)
            if cached_result:
                print(f"Cache HIT for query: {query_text}")
                return cached_result

        parsed_query = self.nlp.parse_query(query_text)
        
        if override_intent and override_intent != "Auto (NLP Pipeline)":
            if override_intent == "Intent via LLM":
                intent = self._classify_intent_via_llm(query_text)
                intent_score = 1.0
            else:
                intent = override_intent
                if intent == "COMPARE":
                    intent = "VISUALIZE+EXPLAIN"
                intent_score = 1.0
            parsed_query["intent"] = intent
            parsed_query["intent_score"] = intent_score
        else:
            intent = parsed_query["intent"]
            intent_score = parsed_query["intent_score"]
            
        filters = parsed_query["filters"]
        
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

        try:
            if intent == "SEARCH":
                self._handle_search(parsed_query, result, threshold=threshold, max_results=max_results)
            elif intent in ("ANALYTICS", "VISUALIZE+EXPLAIN", "COMPARE"):
                self._handle_analytics(parsed_query, result)
            elif intent == "REPORT":
                result.update({
                    "type": "report",
                    "data": {
                        "year": filters.get("year", datetime.datetime.now().year),
                        "month": filters.get("month", datetime.datetime.now().month)
                    }
                })
        except Exception as e:
            print(f"Error during query execution: {e}")
            suggestion = self.suggest_corrected_query(query_text)
            if suggestion:
                result.update({
                    "type": "text_stream",
                    "data": [f"An error occurred while processing your request. Do you mean \"{suggestion}\"?"],
                    "citations": []
                })
            else:
                raise e
            
        return result

    def _classify_intent_via_llm(self, query_text):
        """Uses the LLM to classify the query's intent."""
        system_prompt = (
            "You are an AI classifier that maps queries to one of the following exact intents:\n"
            "- VISUALIZE+EXPLAIN (asking for a chart/graph/plot, comparing product models, categories, trouble codes, or failure rates)\n"
            "- REPORT (asking for monthly or annual quality reports, PDF/Word files, or exporting reports)\n"
            "- ANALYTICS (asking for metrics, statistics, top counts, total failures, frequencies, percentages, or averages)\n"
            "- SEARCH (finding specific incidents, looking up repair steps, search details of a trouble code or VIN)\n\n"
            "Return ONLY the exact intent name from the list above. Do not output anything else."
        )
        prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\nQuery: {query_text}\nIntent:<|end|>\n<|assistant|>\n"
        try:
            llm_client = get_llm()
            intent_raw = llm_client.generate_summary(prompt, max_tokens=15).upper().strip()
            for possible_intent in ["VISUALIZE+EXPLAIN", "COMPARE", "REPORT", "ANALYTICS", "SEARCH"]:
                if possible_intent in intent_raw:
                    if possible_intent == "COMPARE":
                        return "VISUALIZE+EXPLAIN"
                    return possible_intent
            return "SEARCH"
        except Exception as e:
            print(f"Error classifying intent via LLM: {e}")
            return "SEARCH"

    def suggest_corrected_query(self, query_text):
        """Uses the LLM to suggest a valid alternative query based on the database context."""
        schema_info = (
            "Actual SQLite Database Schema:\n"
            "- Table 'records': contains columns [id, ftir_no, product_model_code, sales_model_code, segmentation, vin, engine_no, transmission_no, reported_company, issued_company, outbreak_country, subject, customer_complaint, trouble_code_complaint, trouble_code_defect, checked_contents, checked_results, repair_status, repair_contents, problem_solved, causal_parts_no, causal_parts_name, quality, using_km_int, report_year, report_month, is_resolved]\n"
        )
        system_prompt = (
            "You are an expert technical QA assistant. The user asked a query that returned no results, threw an error, or was not understood. "
            "Recommend a valid alternative query that matches the actual schema patterns in the database.\n"
            f"{schema_info}\n"
            "Rules:\n"
            "1. The suggested query MUST ALWAYS be written in user-friendly natural language. Do NOT output SQL syntax.\n"
            "2. Translate SQL queries into clean natural language questions.\n"
            "3. Return ONLY the suggested query string inside double quotes. Do not output anything else."
        )
        prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\nFailed Query: {query_text}<|end|>\n<|assistant|>\n"
        try:
            llm_client = get_llm()
            import re
            suggestion = llm_client.generate_summary(prompt, max_tokens=30).strip()
            match = re.search(r'"([^"]+)"', suggestion)
            if match:
                return match.group(1)
            return suggestion.replace('"', '')
        except Exception as e:
            print(f"Error suggesting corrected query: {e}")
            return None

    def _handle_search(self, parsed_query, result, threshold=None, max_results=15):
        """Processes hybrid vector search + LLM response generation."""
        query_text = parsed_query["query"]
        from core.rag.rag_retriever import Retriever
        retriever = Retriever(db_path=self.db_path, nlp=self.nlp)
        
        retrieval_res = retriever.retrieve(query_text, threshold=threshold, max_results=max_results, parsed_query=parsed_query)
        records = retrieval_res["records"]
        threshold_used = retrieval_res["threshold"]
        scores = retrieval_res["scores"]
        count = retrieval_res["count"]
        total_candidates = retrieval_res["total_candidates"]
        
        if count == 0:
            query_intent = result.get("intent", "SEARCH")
            if query_intent == "SEARCH":
                suggestion = self.suggest_corrected_query(query_text)
                msg = f"No sufficiently similar technical incidents found (threshold={threshold_used:.2f})."
                if suggestion:
                    msg += f" Do you mean \"{suggestion}\"?"
                result.update({
                    "type": "text_stream",
                    "data": [msg],
                    "citations": [],
                    "threshold_used": threshold_used,
                    "row_count": 0,
                    "score_range": "0.0 - 0.0"
                })
            else:
                system_prompt = "You are a helpful automotive engineering assistant. Answer the user's question using your general knowledge."
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query_text}
                ]
                result.update({
                    "type": "text_stream",
                    "data": messages,
                    "citations": [],
                    "threshold_used": threshold_used,
                    "row_count": 0,
                    "score_range": "0.0 - 0.0"
                })
            return
            
        citations = []
        for rec in records:
            citations.append({
                "ftir_no": rec["ftir_no"],
                "subject": rec["subject"],
                "reported_company": rec["reported_company"],
                "quality": rec["quality"],
                "outbreak_country": rec["outbreak_country"]
            })
            
        MAX_LLM_CASES = 5
        MAX_FIELD_CHARS = 200

        def _truncate(text, max_chars):
            if not text:
                return ""
            return str(text)[:max_chars] + "..." if len(str(text)) > max_chars else str(text)

        llm_records = records[:MAX_LLM_CASES]
        llm_scores = scores[:MAX_LLM_CASES]

        cases_text = []
        for rank, (rec, score) in enumerate(zip(llm_records, llm_scores), 1):
            cases_text.append(
                f"--- Case {rank} | FTIR No: {rec['ftir_no']} | Similarity: {score:.3f} ---\n"
                f"Model: {rec['product_model_code']} | Country: {rec['outbreak_country']}\n"
                f"Complaint: {_truncate(rec['customer_complaint'], MAX_FIELD_CHARS)}\n"
                f"DTC/Checked: {_truncate(rec['checked_results'], MAX_FIELD_CHARS)}\n"
                f"Repair: {_truncate(rec['repair_contents'], MAX_FIELD_CHARS)}\n"
                f"Causal Part: {rec['causal_parts_name']}\n"
            )
            
        context = f"Retrieved FTIR Cases (threshold={threshold_used:.2f}, {count} cases matched):\n\n" + "\n".join(cases_text)
        
        # Optimization: Return static text instead of LLM messages to skip streaming latency
        data = [f"Found {count} relevant cases for your query. Please review the details below."]
        
        score_range = f"{min(scores):.3f} - {max(scores):.3f}" if scores else "0.000 - 0.000"
        
        result.update({
            "type": "text_stream",
            "data": data,
            "citations": citations,
            "threshold_used": threshold_used,
            "row_count": count,
            "score_range": score_range,
            "scores_list": scores
        })

    def _handle_analytics(self, parsed_query, result):
        """Processes SQL queries for analytics & plotting."""
        query_text = parsed_query["query"]
        intent = parsed_query["intent"]
        filters = parsed_query["filters"]
        entities = parsed_query["entities"]
        
        df = pd.DataFrame()
        sql_query_used = None
        
        # Try static query engine first for speed
        model = entities.get("PRODUCT_MODEL")[0] if entities.get("PRODUCT_MODEL") else None
        segment = filters.get("segmentation")
        q = query_text.lower()
        
        if "dealer" in q or "company" in q:
            df, sql_query_used = self.analytics_engine.get_top_dealers_or_countries("dealer", limit=filters.get("limit", 10), country=entities.get("COUNTRY")[0] if entities.get("COUNTRY") else None)
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

        # Fallback to dynamic SQL if static query returned empty data
        if df is None or df.empty:
            try:
                print("Static query returned empty, falling back to dynamic SQL generation...")
                sql_query_used = generate_sql(query_text)
                df, err = execute_sql(None, sql_query_used)
                if err or df is None or df.empty:
                    df = pd.DataFrame()
            except Exception as e:
                print(f"Dynamic SQL failed: {e}")
                df = pd.DataFrame()

        if df.empty:
            suggestion = self.suggest_corrected_query(query_text)
            msg = "No data available to analyze."
            if suggestion:
                msg = f"No data available to analyze. Do you mean \"{suggestion}\"?"
            result.update({
                "type": "text_stream",
                "data": [msg]
            })
            return

        # Select Chart Type
        from core.sql.sql_executor import AnalyticsEngine as AE
        from analytics.graph_selector import select_chart_type
        chart_type, chart_title = select_chart_type(intent, df, query_text)
            
        df_for_llm = df.iloc[:20, :6]
        if len(df) > 20 or len(df.columns) > 6:
            if "mileage" in df.columns or "km" in df.columns:
                markdown_table = df.describe().to_markdown()
            else:
                markdown_table = df_for_llm.to_markdown(index=False) + f"\n\n*(Table truncated to top 20 rows of {len(df)} results)*"
        else:
            markdown_table = df.to_markdown(index=False)
            
        if len(markdown_table) > 6000:
            markdown_table = markdown_table[:6000] + "\n\n*(Truncated)*"
        
        # Optimization: skip LLM explanation to significantly improve latency
        messages = []
        
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


# =====================================================
# ✅ SAFE EXECUTION
# =====================================================
def safe_execute(code, df):
    for attempt in range(2):
        try:
            exec_result = executor.execute(code, df)
            if exec_result["success"]:
                return exec_result["result"], {}, [], None
            else:
                error = exec_result["error"]
        except Exception as e:
            error = str(e)

        print(f"\n❌ Execution Error (attempt {attempt+1}):\n{error}")
        try:
            code = fix_code(code, error)
            code = ensure_result_assignment(code)
        except Exception as fix_err:
            return None, None, [], str(fix_err)

    return None, None, [], error


def select_best_data(result, env):
    if isinstance(result, (pd.DataFrame, pd.Series)):
        return result
    candidates = [v for v in env.values() if isinstance(v, (pd.DataFrame, pd.Series))]
    if candidates:
        return max(candidates, key=lambda x: len(x))
    return result


# =====================================================
# ✅ MAIN PIPELINE (DataFrame-based Agentic)
# =====================================================
def run_pipeline(query, df):
    print("\n🔹 Starting Pandas Pipeline...\n")
    base_instructions = "Analyze dataset and extract insights"

    intents, kpis, filters, aggregations = intent_engine.build_intent_prompt(
        base_instructions=base_instructions,
        question=query
    )

    code_raw = generate_code(query, df.columns)
    code = ensure_result_assignment(code_raw)

    result, env, images, error = safe_execute(code, df)
    if error:
        return {"error": error}

    best_data = select_best_data(result, env)

    viz_output = None
    try:
        viz_output = visualizer.visualize(best_data, intents=intents, kpis=kpis)
    except Exception as e:
        print("⚠️ Visualization failed:", e)

    insights = generate_insights(query, best_data)
    summary = summarize(insights)

    output = {
        "mode": "PYTHON",
        "code": code,
        "result": result,
        "images": images,
        "visualization": viz_output,
        "insights": insights,
        "summary": summary,
        "intent": intents,
        "kpis": kpis,
        "filters": filters,
        "aggregations": aggregations
    }

    memory.add(query, str(result))
    print("\n✅ Pipeline completed successfully\n")
    return output