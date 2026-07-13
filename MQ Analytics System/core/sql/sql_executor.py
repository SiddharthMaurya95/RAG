import sqlite3
import pandas as pd
from core.paths import get_db_path

def execute_sql(conn, query):
    if conn is None:
        from core.database import get_engine
        conn = get_engine(get_db_path()).connect()
    try:
        df = pd.read_sql_query(query, conn)
        return df, None
    except Exception as e:
        return None, str(e)

class AnalyticsEngine:
    def __init__(self, db_path="data/automotive.db"):
        self.db_path = get_db_path(db_path)

    def _get_connection(self):
        from core.database import get_engine
        return get_engine(self.db_path).connect()


    def get_top_dealers_or_countries(self, by="dealer", limit=10, year=None, country=None):
        """Returns top N dealers or countries with failure counts."""
        conn = self._get_connection()
        
        # Build query dynamically based on parameters
        where_clauses = []
        params = []
        if year:
            where_clauses.append("report_year = ?")
            params.append(year)
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

    def get_monthly_failure_trend(self, year=None, model=None):
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

    def get_model_comparison(self):
        """Computes comprehensive failure stats per product model."""
        conn = self._get_connection()
        query = """
            SELECT 
                product_model_code as model, 
                COUNT(*) as total_claims,
                ROUND(AVG(using_km_int), 1) as avg_mileage,
                ROUND(SUM(is_resolved) * 100.0 / COUNT(*), 1) as resolution_rate,
                SUM(CASE WHEN LOWER(quality) = 'poor' THEN 1 ELSE 0 END) as poor_quality_count
            FROM records
            WHERE product_model_code IS NOT NULL AND product_model_code != ''
            GROUP BY product_model_code
            ORDER BY total_claims DESC;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df, query.strip()

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

    def get_repair_success_rate(self):
        """Returns resolution percentages grouped by trouble code."""
        conn = self._get_connection()
        query = """
            SELECT 
                trouble_code_complaint as trouble_code,
                COUNT(*) as total_cases,
                ROUND(SUM(is_resolved) * 100.0 / COUNT(*), 1) as success_rate
            FROM records
            WHERE trouble_code_complaint IS NOT NULL AND trouble_code_complaint != ''
            GROUP BY trouble_code_complaint
            HAVING total_cases >= 5
            ORDER BY success_rate DESC;
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df, query.strip()

    def get_failed_parts_frequency(self, limit=10, model=None, segmentation=None):
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

    def query_via_llm(self, query_text):
        """Generates and executes a SQLite query based on user request using the local LLM."""
        from core.singletons import get_llm
        from core.database import Record
        llm_client = get_llm()

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
- sbpr_no: Unique ID of substantial safety-regulatory problems (e.g. brakes/steering/immobile)
- ftir_no: Field Technical Incident Report number (unique key)
- ftir_report_date / reply_date: Report creation date / closure date (YYYY-MM-DD)
- status: Report state (e.g. 'Open', 'Closed')
- product_model_code / sales_model_code: Internal product model (starts with Y) / market model code (starts with letters)
- segmentation: Vehicle system/area (e.g., Engine, Transmission, Body)
- using_km_int: Odometer/mileage at time of issue in kilometers (integer)
- reported_company: Dealership or distributor reporting the issue
- outbreak_country: Country where incident/defect occurred/originated
- subject: Brief summary/verbatim of the reported technical issue
- customer_complaint: Detailed verbatim description of complaint symptoms
- trouble_code_complaint / trouble_code_defect: DTC trouble code reported / trouble code description
- checked_contents / checked_results: Actions taken / diagnostic findings & inspection details
- repair_status / repair_contents: Status of repair / repair actions details (e.g., replaced parts)
- causal_parts_no / causal_parts_name: Faulty part number / name
- quality: Incident quality level rating ('Good', 'Moderate', 'Poor')
- report_year / report_month: Computed year / month of report
- is_resolved: Binary status (1 if resolved/fixed, 0 otherwise)

========================================
UNDERSTOOD USER INTENT (IMPORTANT)
========================================
Use structured database matching logic:
- Apply WHERE clause filters (e.g. year, model, country) before aggregating.
- Use correct SQLite aggregation metrics (COUNT, AVG, SUM) matching KPIs.
- Use GROUP BY and ORDER BY clauses as matching user's requested comparison/groupings.

=======================================
CRITICAL RULES (DO NOT BREAK)
========================================
1. OUTPUT FORMAT:
- Output ONLY a raw SQLite SELECT statement.
- Do NOT wrap the query in code blocks (e.g., no ```sql).
- Do NOT explain the query.

2. DATA USAGE:
- Always query from the 'records' table.

3. MAPPING RULES:
- Map misspelled/short columns correctly:
  complaint -> customer_complaint, checked -> checked_contents, result -> checked_results,
  repair -> repair_contents, part -> causal_parts_name, model -> product_model_code,
  sales model -> sales_model_code, year -> report_year, month -> report_month,
  country -> outbreak_country, dealer/company -> reported_company.
- Never use singular names: Use 'checked_contents', 'checked_results', 'causal_parts_name'.
- Use LOWER(col) LIKE '%value%' for text searches instead of = (e.g. LOWER(reported_company) LIKE '%maruti suzuki%').
- For partial model/DTC codes, use LIKE 'value%' (e.g. product_model_code LIKE 'YNC%').

4. QUERY LIMITS:
- CRITICAL: Do NOT set any LIMIT clause in the SQL query unless a limit is explicitly and literally requested in the user query (e.g., 'top 10', 'limit 5'). Never add LIMIT 10 by default or as a fallback for charts/groupings. If the user asks to compare models or show counts (e.g., "each product_model_code"), you must retrieve all of them without any LIMIT.

========================================
FEW-SHOT EXAMPLES (FOLLOW EXACTLY)
========================================
Input: Compare failure rates of model YNC412 vs YFG121
Output: SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE product_model_code IN ('YNC412', 'YFG121') GROUP BY product_model_code

Input: Compare YNC and YSD models
Output: SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE product_model_code LIKE 'YNC%' OR product_model_code LIKE 'YSD%' GROUP BY product_model_code

Input: Compare ATM and ERT sales models
Output: SELECT sales_model_code, COUNT(*) as failure_count FROM records WHERE sales_model_code LIKE 'ATM%' OR sales_model_code LIKE 'ERT%' GROUP BY sales_model_code

Input: Compare trouble code frequency for P03 and P04
Output: SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE trouble_code_complaint LIKE 'P03%' OR trouble_code_complaint LIKE 'P04%' GROUP BY trouble_code_complaint

Input: Compare failures in India vs Brunei
Output: SELECT outbreak_country, COUNT(*) as failure_count FROM records WHERE LOWER(outbreak_country) IN ('india', 'brunei') GROUP BY outbreak_country

Input: Show trouble code frequency for model YEC222
Output: SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE LOWER(product_model_code) = 'yec222' GROUP BY trouble_code_complaint ORDER BY count DESC

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

            response = llm(
                prompt,
                max_tokens=MAX_GEN_TOKENS,
                temperature=0.1,
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

            print(f"Generated and parsed Dynamic LLM SQL query (Attempt {attempt + 1}):\n{sql_query}")

            conn = self._get_connection()
            try:
                df = pd.read_sql_query(sql_query, conn)
                conn.close()
                return df, sql_query
            except Exception as e:
                conn.close()
                last_sql = sql_query
                last_error = str(e)
                print(f"Failed to execute LLM SQL query on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    raise e

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

