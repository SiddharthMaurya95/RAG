import sqlite3
import pandas as pd
import sys
from core.paths import get_db_path
from core.logger import get_logger
from core.custom_exception import CustomException
from core.decorators import with_logging_and_exceptions

logger = get_logger(__name__)

class AnalyticsEngine:
    def __init__(self, db_path="data/automotive.db"):
        self.db_path = get_db_path(db_path)

    def _get_connection(self):
        from core.database import get_engine
        return get_engine(self.db_path).connect()


    @with_logging_and_exceptions
    def get_top_dealers_or_countries(self, by="dealer", limit=10, year=None, country=None, model=None):
        """Returns top N dealers or countries with failure counts."""
        conn = self._get_connection()
        
        # Build query dynamically based on parameters
        where_clauses = []
        params = []
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if model:
            where_clauses.append("product_model_code = ?")
            params.append(model)
        if country and by != "country":
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        if by == "dealer":
            query = f"""
                SELECT COALESCE(reported_company, 'Unknown') as dealer, COUNT(*) as failures
                FROM records
                {where_str}
                GROUP BY reported_company
                ORDER BY failures DESC
                LIMIT ?;
            """
        else: # country
            query = f"""
                SELECT COALESCE(outbreak_country, 'Unknown') as country, COUNT(*) as failures
                FROM records
                {where_str}
                GROUP BY outbreak_country
                ORDER BY failures DESC
                LIMIT ?;
            """
            
        params.append(limit)
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_trouble_code_frequency(self, limit=10, model=None, segmentation=None, year=None, country=None):
        """Returns failure counts for each trouble code."""
        conn = self._get_connection()
        where_clauses = ["trouble_code_complaint IS NOT NULL AND trouble_code_complaint != ''"]
        params = []
        if model:
            where_clauses.append("product_model_code = ?")
            params.append(model)
        if segmentation:
            where_clauses.append("segmentation = ?")
            params.append(segmentation)
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if country:
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        query = f"""
            SELECT trouble_code_complaint as trouble_code, COUNT(*) as count
            FROM records
            {where_str}
            GROUP BY trouble_code_complaint
            ORDER BY count DESC
            LIMIT ?;
        """
        params.append(limit)
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_monthly_failure_trend(self, year=None, model=None, country=None):
        """Returns chronological monthly failure trends, applying Pandas resampling/ordering."""
        conn = self._get_connection()
        where_clauses = ["report_year > 0 AND report_month > 0"]
        params = []
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if model:
            where_clauses.append("product_model_code = ?")
            params.append(model)
        if country:
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        query = f"""
            SELECT report_year, report_month, COUNT(*) as failures
            FROM records
            {where_str}
            GROUP BY report_year, report_month
            ORDER BY report_year ASC, report_month ASC;
        """
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        
        # Post-process with Pandas to format dates neatly for plotting (e.g. '2024-05')
        if not df.empty:
            df['period'] = df.apply(lambda r: f"{int(r['report_year'])}--{int(r['report_month']):02d}", axis=1)
        return df, query.strip()

    @with_logging_and_exceptions
    def get_model_comparison(self, year=None, country=None):
        """Computes comprehensive failure stats per product model."""
        conn = self._get_connection()
        where_clauses = ["product_model_code IS NOT NULL AND product_model_code != ''"]
        params = []
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if country:
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        query = f"""
            SELECT 
                product_model_code as model, 
                COUNT(*) as total_claims,
                ROUND(AVG(using_km_int), 1) as avg_mileage,
                ROUND(SUM(is_resolved) * 100.0 / COUNT(*), 1) as resolution_rate,
                SUM(CASE WHEN LOWER(quality) = 'poor' THEN 1 ELSE 0 END) as poor_quality_count
            FROM records
            {where_str}
            GROUP BY product_model_code
            ORDER BY total_claims DESC;
        """
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_using_km_distribution(self, model=None):
        """Returns the mileage values binned into intervals for histograms."""
        conn = self._get_connection()
        where_clause = "WHERE using_km_int > 0"
        params = []
        if model:
            where_clause += " AND product_model_code = ?"
            params.append(model)
            
        query = f"SELECT using_km_int as mileage FROM records {where_clause};"
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_quality_distribution(self, model=None, year=None, country=None):
        """Returns counts for each quality rating."""
        conn = self._get_connection()
        where_clauses = []
        params = []
        if model:
            where_clauses.append("product_model_code = ?")
            params.append(model)
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if country:
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"""
            SELECT COALESCE(quality, 'Unknown') as quality, COUNT(*) as count
            FROM records
            {where_clause}
            GROUP BY quality;
        """
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_repair_success_rate(self, year=None, model=None, country=None):
        """Returns resolution percentages grouped by trouble code."""
        conn = self._get_connection()
        where_clauses = ["trouble_code_complaint IS NOT NULL AND trouble_code_complaint != ''"]
        params = []
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if model:
            where_clauses.append("product_model_code = ?")
            params.append(model)
        if country:
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        query = f"""
            SELECT 
                trouble_code_complaint as trouble_code,
                COUNT(*) as total_cases,
                ROUND(SUM(is_resolved) * 100.0 / COUNT(*), 1) as success_rate
            FROM records
            {where_str}
            GROUP BY trouble_code_complaint
            HAVING total_cases >= 5
            ORDER BY success_rate DESC;
        """
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_failed_parts_frequency(self, limit=10, model=None, segmentation=None, year=None, country=None):
        """Returns failure counts for each causal part name."""
        conn = self._get_connection()
        where_clauses = ["causal_parts_name IS NOT NULL AND causal_parts_name != ''"]
        params = []
        if model:
            where_clauses.append("product_model_code = ?")
            params.append(model)
        if segmentation:
            where_clauses.append("segmentation = ?")
            params.append(segmentation)
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
        if country:
            where_clauses.append("outbreak_country = ?")
            params.append(country)
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        query = f"""
            SELECT causal_parts_name as part_name, COUNT(*) as count
            FROM records
            {where_str}
            GROUP BY causal_parts_name
            ORDER BY count DESC
            LIMIT ?;
        """
        params.append(limit)
        df = pd.read_sql_query(query, conn, params=tuple(params))
        conn.close()
        return df, query.strip()

    @with_logging_and_exceptions
    def get_overall_resolution_stats(self):
        """Returns overall counts of resolved vs unresolved records."""
        conn = self._get_connection()
        query = """
            SELECT 
                CASE WHEN is_resolved = 1 THEN 'Resolved' ELSE 'Unresolved' END as status,
                COUNT(*) as count
            FROM records
            GROUP BY is_resolved;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df, query.strip()

    def query_via_llm(self, query_text: str, target_df: pd.DataFrame = None, tracker=None):
        """Generates and executes a SQLite query based on user request using the local LLM."""
        logger.info(f"AnalyticsEngine starting query_via_llm for: '{query_text}'")
        from core.singletons import get_llm
        from core.database import Record
        from analytics.intent_classifier import Intent_classification
        
        llm_client = get_llm()
        
        intent_engine = Intent_classification()
        logger.info("Extracting intents via intent_engine for SQL generation.")
        intents, kpis, filters, aggregations = intent_engine.build_intent_prompt(query_text)
        intent_summary = f"""
Intents: {', '.join(intents) if intents else 'None'}
KPIs: {', '.join(kpis) if kpis else 'None'}
Filters: {', '.join(filters) if filters else 'None'}
Aggregations: {', '.join(aggregations) if aggregations else 'None'}
"""
        # Model context configuration — must match n_ctx in client.py
        MODEL_N_CTX = 4096
        MAX_GEN_TOKENS = 256  # reserved for the generated SQL output
        # Safety: 4 characters ≈ 1 token (rough estimate)
        MAX_PROMPT_CHARS = (MODEL_N_CTX - MAX_GEN_TOKENS) * 4

        # Dynamically extract database schema context from SQLAlchemy Record mapper
        # Emit only column names (no type/nullable) to keep token count minimal
        col_names = ", ".join(
            column.key for column in Record.__mapper__.columns
        )

        # Compact system prompt styled like the reference prompt structure
        system_prompt = f"""You are a SQLite expert.

Your task is to write a syntactically correct SQLite query to answer the user query.

========================================
DATASET CONTEXT
========================================
This database table represents FTIR (Field Technical Information Report) data.
Includes vehicle system segmentation, causal parts, customer complaints, VIN, and repair status.

Table: records
Columns:
{col_names}

========================================
COLUMN SEMANTICS (GUIDE)
========================================
SBPR No.: Substantial problem unique ID
FTIR No.: Field Technical Information Report number
Causal Parts Name (English): Name of faulty part
Product Model Code: Internal product/model identifier
Sales Model Code: Sales model identifier for market
Segmentation: Faulty Part Related Vehicle System
Subject (English): Customer/dealer verbatim for the Reported issue
Causal Parts No.: Number of faulty part
Rank: Severity or priority ranking of issue: A Rank means Safety-Regulatory-Vehicle immobile, B Rank: means all other issues, 
C Rank: means Customer Feedback 
Reported Country: Country where issue was reported
VIN: Vehicle Identification Number
Report Company: Company reporting the FTIR/issue
Issued Company: Company issuing the FTIR
FTIR Report Date: Date when FTIR report was created
Reply Date: FTIR CLOSURE DATE
Status: Current state of FTIR report 
FC-OK: Manufacturing Date of the Vehicle
Date Registered: Date vehicle was registered
Date of Incident: Date When issue occurred
Mileage / Using Time: Mileage Usage at time of issue(odometer reading in KM)
Days Used: Number of days vehicle used before issue from registeration date
FPCR No.: Field Problem Countermeasure Report NUMBER (FPCR Consist of investing details, rootcause, countermeasure, VIN cutoff and cutoff date
, Responsible Department and alert figures)
Engine No.: Engine number identifier
Transmission No.: Transmission Number identifier
Outbreak Country: Country where defect originated
Sales Dealer: Dealer who sold vehicle
Service Dealer: Dealer who serviced vehicle
Spec on Destination: Regional specification of vehicle
Collection Request Date: Date when part collection requested
Parts Retrieved Date: Date when defective part received at Plant
Manufacturer Factory: Manufacturing plant
Person of Action Judgement: Individual resposible for investigation and analysis of FTIR 
Department of Action Judgement: MQ Department of Person of Action Judgement
Judgement Date: Decision date by Person of Action Judgement
Action Judgement: Decision taken for Closing FTIR
Reason of "Not to File as an SBPR": Justification for closing FTIR at FTIR Level without superseeding
Approval Judgement Date: Final approval date of FTIR
root_cause: Identified root cause of failure derived from customer complaint, investigation results, and causal parts.

========================================
UNDERSTOOD USER INTENT (IMPORTANT)
========================================
{intent_summary}

Use structured database matching logic:
- Apply WHERE clause filters (e.g. year, model, country) before aggregating, matching the Filters above.
- Use correct SQLite aggregation metrics (COUNT, AVG, SUM) matching the KPIs above.
- Use GROUP BY and ORDER BY clauses matching the Aggregations above.

=======================================
CRITICAL RULES (DO NOT BREAK)
=======================================
1. OUTPUT FORMAT:
- Output ONLY a raw SQLite SELECT statement.
- Do NOT wrap the query in code blocks (e.g., no ```sql).
- Do NOT explain the query.

2. DATA USAGE:
- Always query from the 'records' table.
- CRITICAL: Only use columns defined in the schema above. Do NOT assume, invent, or use generic columns like 'name', 'vehicle', 'department', 'involved', or 'question' under any circumstances.

3. MAPPING RULES:
- If the user query does not explicitly specify a column and asks for records related to a generic term (e.g. "related to engine", "about brake"), ALWAYS use the 'subject' column for filtering (e.g. LOWER(subject) LIKE '%engine%'). Never use 'ftir_no' for generic text searches.
- If the user query asks for "issues", "major issues", "problems", or "major problems", always use the 'subject' column to represent the issues/problems (e.g. SELECT subject, COUNT(*) as count ... GROUP BY subject).
- Map misspelled/short columns correctly:
  complaint -> customer_complaint, checked -> checked_contents, result -> checked_results,
  repair -> repair_contents, part -> causal_parts_name, model -> product_model_code,
  sales model -> sales_model_code, year -> report_year, month -> report_month,
  country -> outbreak_country, reported country -> reported_country,
  dealer/company -> reported_company, sales dealer -> sales_dealer, service dealer -> service_dealer,
  department/dept/dept. -> dept_of_action_judgement, days -> days_used,
  person/investigator -> person_of_action_judgement, judgement date -> judgement_date,
  approval date -> approval_judgement_date.
- Whenever "department" is concerned or mentioned, ALWAYS use the 'dept_of_action_judgement' column.
- 'MQ' or 'mq' represents a department and maps to the expanded prefix 'Quality Assurance Market Quality'. If the query mentions 'MQ [Number]' or 'mq [Number]' (e.g. 'MQ 7', 'MQ 6'), interpret it as 'Quality Assurance Market Quality-[Number]' (with a hyphen) when filtering on the 'dept_of_action_judgement' column (e.g. dept_of_action_judgement = 'Quality Assurance Market Quality-7').
- Never use singular names: Use 'checked_contents', 'checked_results', 'causal_parts_name'.
- Whenever "resolved", "are resolved", or "solved" is mentioned, ALWAYS use the condition `is_resolved = 1` in the WHERE clause. Do NOT check for `status = 'resolved'`.
- Use LOWER(col) LIKE '%value%' for text searches instead of = (e.g. LOWER(reported_company) LIKE '%maruti suzuki%').
- For partial model, sales model, or DTC/trouble codes (e.g., 'YHB', 'YNC', 'P03'), always use prefix matching with LIKE 'PREFIX%' (e.g. product_model_code LIKE 'YHB%', trouble_code_complaint LIKE 'P03%'). NEVER use LOWER() or omit the trailing % wildcard.

4. QUERY LIMITS:
- CRITICAL: Do NOT set any LIMIT clause in the SQL query unless a limit is explicitly and literally requested in the user query (e.g., 'top 10', 'limit 5'). Never add LIMIT 10 by default or as a fallback for charts/groupings. If the user asks to compare models or show counts (e.g., "each product_model_code"), you must retrieve all of them without any LIMIT.
- CRITICAL: If the user query explicitly requests a limit (e.g., 'top 10', 'limit 5', 'first 10'), you MUST include the LIMIT clause (e.g., LIMIT 10) in the SQL query.

========================================
FEW-SHOT EXAMPLES (FOLLOW EXACTLY)
========================================
Input: show all records for MQ 7 department
Output: SELECT * FROM records WHERE dept_of_action_judgement = 'Quality Assurance Market Quality-7'

Input: count of ftir for YHB model with model name
Output: SELECT product_model_code, COUNT(*) as total_count FROM records WHERE product_model_code LIKE 'YHB%' GROUP BY product_model_code

Input: give me a bar chart for top 10 most failed parts
Output: SELECT causal_parts_name, COUNT(*) as count FROM records GROUP BY causal_parts_name ORDER BY count DESC LIMIT 10

Input: Compare YNC and YSD models
Output: SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE product_model_code LIKE 'YNC%' OR product_model_code LIKE 'YSD%' GROUP BY product_model_code

Input: Compare failures in India vs Brunei
Output: SELECT outbreak_country, COUNT(*) as failure_count FROM records WHERE LOWER(outbreak_country) IN ('india', 'brunei') GROUP BY outbreak_country

Input: give me total number of ftir whose report company is maruti suzuki
Output: SELECT COUNT(*) as count FROM records WHERE LOWER(reported_company) LIKE '%maruti suzuki%'"""

        # Assemble base prompt in Phi-3 native template format
        base_prompt = (
            f"<|system|>\n{system_prompt}<|end|>\n"
            f"<|user|>\nCreate a SQLite query to answer: '{query_text}'<|end|>\n"
            f"<|assistant|>\n"
        )

        # Guard: hard-cap the prompt to avoid exceeding n_ctx
        if len(base_prompt) > MAX_PROMPT_CHARS:
            base_prompt = base_prompt[-MAX_PROMPT_CHARS:]
            # Ensure the prompt still starts cleanly at an assistant tag
            if "<|assistant|>" not in base_prompt:
                base_prompt = "<|assistant|>\n"

        llm = llm_client.load_model()
        max_retries = 4

        for attempt in range(max_retries):
            # On retries, build a compact correction prompt instead of appending to the
            # base prompt (which would grow unboundedly and overflow the context window).
            if attempt == 0:
                prompt = base_prompt
            else:
                # Compact retry prompt: only the error + failed SQL, no full system block
                prompt = (
                    f"<|system|>\nYou are a SQLite expert. Fix the SQL error and return ONLY the corrected raw SQL statement for the 'records' table.<|end|>\n"
                    f"<|user|>\nOriginal question: '{query_text}'\n"
                    f"Failed SQL: {last_sql}\n"
                    f"Error: {last_error}\n"
                    f"Corrected SQL:<|end|>\n"
                    f"<|assistant|>\n"
                )
                # Safety cap on retry prompt as well
                if len(prompt) > MAX_PROMPT_CHARS:
                    prompt = prompt[-MAX_PROMPT_CHARS:]

            if tracker and attempt == 0:
                tracker.start_stage("Generating SQL")

            logger.info(f"Invoking LLM for SQL generation (Attempt {attempt + 1})")
            response = llm(
                prompt,
                max_tokens=MAX_GEN_TOKENS,
                temperature=0.0,
                stop=["<|end|>", "<|user|>"],
                echo=False
            )

            sql_query = response["choices"][0]["text"].strip()

            # Extract SQL starting from SELECT (discarding conversational introductions)
            select_idx = sql_query.upper().find("SELECT")
            if select_idx != -1:
                sql_query = sql_query[select_idx:]

            # Strip code-block fences if the LLM wrapped the output
            if "```" in sql_query:
                lines = sql_query.split("\n")
                sql_lines = []
                in_code = False
                for line in lines:
                    if line.startswith("```"):
                        in_code = not in_code
                        continue
                    if in_code or not sql_query.startswith("```"):
                        sql_lines.append(line)
                sql_query = "\n".join(sql_lines).strip()

            # Truncate at the first semicolon to discard any postamble
            semicolon_idx = sql_query.find(";")
            if semicolon_idx != -1:
                sql_query = sql_query[:semicolon_idx].strip()

            sql_query = sql_query.strip().rstrip(";")

            # Remove LLM-generated LIMIT clause if the user query does not explicitly specify a numeric limit
            import re
            limit_match = re.search(r'\bLIMIT\s+(\d+)\b', sql_query, re.IGNORECASE)
            if limit_match:
                q_text_lower = query_text.lower()
                has_digit = any(char.isdigit() for char in q_text_lower)
                limit_patterns = [
                    r'\btop\s+\d+',
                    r'\blimit\s+\d+',
                    r'\bfirst\s+\d+',
                    r'\bbest\s+\d+',
                    r'\bworst\s+\d+',
                    r'\bmost\s+\d+',
                    r'\bleast\s+\d+'
                ]
                user_has_limit = has_digit and any(re.search(pat, q_text_lower) for pat in limit_patterns)
                if not user_has_limit:
                    sql_query = re.sub(r'\bLIMIT\s+\d+\b', '', sql_query, flags=re.IGNORECASE).strip()

            logger.info(f"Generated and parsed Dynamic LLM SQL query (Attempt {attempt + 1}):\n{sql_query}")

            if tracker:
                tracker.complete_stage("Generating SQL")
                tracker.start_stage("Executing SQL")

            if target_df is not None:
                import sqlite3
                conn = sqlite3.connect(':memory:')
                # Create the table
                target_df.to_sql('records', conn, index=False)
            else:
                conn = self._get_connection()
                
            try:
                df = pd.read_sql_query(sql_query, conn)
                conn.close()
                logger.info("Successfully executed LLM SQL query.")
                if tracker:
                    tracker.complete_stage("Executing SQL")
                return df, sql_query
            except Exception as e:
                conn.close()
                last_sql = sql_query
                last_error = str(e)
                logger.warning(f"Failed to execute LLM SQL query on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    e.failed_sql = last_sql
                    logger.error("All retries exhausted for LLM SQL query execution.")
                    raise CustomException(e, sys)

    @with_logging_and_exceptions
    def get_distinct_models(self):
        """Returns a sorted list of distinct product model codes."""
        conn = self._get_connection()
        query = """
            SELECT DISTINCT product_model_code
            FROM records
            WHERE product_model_code IS NOT NULL AND product_model_code != ''
            ORDER BY product_model_code ASC;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['product_model_code'].tolist()

    @with_logging_and_exceptions
    def get_distinct_countries(self):
        """Returns a sorted list of distinct outbreak countries."""
        conn = self._get_connection()
        query = """
            SELECT DISTINCT outbreak_country
            FROM records
            WHERE outbreak_country IS NOT NULL AND outbreak_country != ''
            ORDER BY outbreak_country ASC;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['outbreak_country'].tolist()

    @with_logging_and_exceptions
    def get_distinct_years(self):
        """Returns a sorted list of distinct report years."""
        conn = self._get_connection()
        query = """
            SELECT DISTINCT report_year
            FROM records
            WHERE report_year > 0
            ORDER BY report_year DESC;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['report_year'].tolist()

    @with_logging_and_exceptions
    def get_avg_resolution_mileage(self, year=None, model=None, country=None):
        """Returns average mileage of resolved records."""
        from sqlalchemy import text
        conn = self._get_connection()
        where_clauses = ["is_resolved = 1", "using_km_int > 0"]
        params = {}
        if year:
            where_clauses.append("report_year = :year")
            params["year"] = year
        if model:
            where_clauses.append("product_model_code = :model")
            params["model"] = model
        if country:
            where_clauses.append("outbreak_country = :country")
            params["country"] = country
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        query = f"SELECT ROUND(AVG(using_km_int), 0) as avg_km FROM records {where_str};"
        try:
            res = conn.execute(text(query), params)
            row = res.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        finally:
            conn.close()

