import sqlite3
import pandas as pd
from core.paths import get_db_path

class AnalyticsEngine:
    def __init__(self, db_path="data/automotive.db"):
        self.db_path = get_db_path(db_path)

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

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
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df, query.strip()

    def get_trouble_code_frequency(self, limit=10, model=None, segmentation=None):
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
        df = pd.read_sql_query(query, conn, params=params)
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
        df = pd.read_sql_query(query, conn, params=params)
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
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df, query.strip()

    def get_quality_distribution(self, model=None):
        """Returns counts for each quality rating."""
        conn = self._get_connection()
        where_clause = ""
        params = []
        if model:
            where_clause = "WHERE product_model_code = ?"
            params.append(model)
            
        query = f"""
            SELECT COALESCE(quality, 'Unknown') as quality, COUNT(*) as count
            FROM records
            {where_clause}
            GROUP BY quality;
        """
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return df, query.strip()

    def get_escalations(self, model=None, country=None, trouble_code=None):
        """Fetches the escalation dashboard showing unresolved poor quality cases, optionally filtered."""
        conn = self._get_connection()
        where_clauses = []
        params = []
        
        # We join with records to filter by product_model_code if model is provided
        if model:
            query = """
                SELECT m.id, m.ftir_no, m.subject, m.reported_company as dealer, 
                       m.outbreak_country as country, m.trouble_code_complaint as trouble_code,
                       m.quality, m.problem_solved
                FROM mv_escalations m
                JOIN records r ON m.id = r.id
                WHERE r.product_model_code = ?
            """
            params.append(model)
            if country:
                query += " AND LOWER(m.outbreak_country) = LOWER(?)"
                params.append(country)
            if trouble_code:
                query += " AND LOWER(m.trouble_code_complaint) = LOWER(?)"
                params.append(trouble_code)
        else:
            query = """
                SELECT id, ftir_no, subject, reported_company as dealer, 
                       outbreak_country as country, trouble_code_complaint as trouble_code,
                       quality, problem_solved
                FROM mv_escalations
            """
            if country:
                where_clauses.append("LOWER(outbreak_country) = LOWER(?)")
                params.append(country)
            if trouble_code:
                where_clauses.append("LOWER(trouble_code_complaint) = LOWER(?)")
                params.append(trouble_code)
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
                
        df = pd.read_sql_query(query, conn, params=params)
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
        df = pd.read_sql_query(query, conn, params=params)
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
        llm_client = get_llm()
        
        # Define strict SQL instructions with few-shot examples
        system_prompt = """You are a SQLite expert. Given an input question, create only a syntactically correct SQLite query to run. Do not wrap the query in code blocks, do not explain the query, and return ONLY the raw SQL statement.

CRITICAL RULES:
- You MUST query from the 'records' table. The database ONLY contains the 'records' table. Do NOT query from any other table (like Failures, model_failures, etc.). All data is in the 'records' table!
- When filtering text columns like 'reported_company', 'outbreak_country', 'causal_parts_name', 'subject', etc., use LIKE '%value%' with LOWER() instead of =. For example, use: LOWER(reported_company) LIKE '%maruti suzuki%' because company names may contain suffixes or extra words like 'MARUTI SUZUKI INDIA LIMITED'.

The 'records' table has the following columns:
- id: INTEGER
- sbpr_no: TEXT
- ftir_no: TEXT
- ftir_report_date: TEXT (YYYY-MM-DD)
- reply_date: TEXT
- status: TEXT
- product_model_code: TEXT
- sales_model_code: TEXT
- segmentation: TEXT (e.g. Engine, Transmission)
- vin: TEXT
- engine_no: TEXT
- transmission_no: TEXT
- using_km_int: INTEGER (cleaned mileage/km)
- reported_company: TEXT (dealer/company name)
- outbreak_country: TEXT
- subject: TEXT
- customer_complaint: TEXT
- trouble_code_complaint: TEXT (Trouble code reported by customer)
- causal_parts_name: TEXT (failed/causal part name)
- quality: TEXT ('Good', 'Moderate', 'Poor')
- report_year: INTEGER
- report_month: INTEGER
- is_resolved: INTEGER (1 if resolved, 0 otherwise)

Examples:
Input: "Compare failure rates of model YNC412 vs YFG121"
Output: SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE product_model_code IN ('YNC412', 'YFG121') GROUP BY product_model_code;

Input: "Compare failures in India vs Brunei"
Output: SELECT outbreak_country, COUNT(*) as failure_count FROM records WHERE LOWER(outbreak_country) IN ('india', 'brunei') GROUP BY outbreak_country;

Input: "Compare trouble code frequency for P0171 and P0300"
Output: SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE trouble_code_complaint IN ('P0171', 'P0300') GROUP BY trouble_code_complaint;

Input: "Show trouble code frequency for model YEC222"
Output: SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE LOWER(product_model_code) = 'yec222' GROUP BY trouble_code_complaint ORDER BY count DESC LIMIT 10;

Input: "give me total number of ftir whose report company is maruti suzuki"
Output: SELECT COUNT(*) as count FROM records WHERE LOWER(reported_company) LIKE '%maruti suzuki%';
"""
        
        # Format explicitly for Phi-3 GGUF native template
        base_prompt = f"<|system|>\n{system_prompt}<|end|>\n<|user|>\nCreate a SQLite query to answer: '{query_text}'<|end|>\n<|assistant|>\n"
        prompt = base_prompt
        
        # Use LLM to generate the query
        llm = llm_client.load_model()
        max_retries = 4
        
        for attempt in range(max_retries):
            response = llm(
                prompt,
                max_tokens=500,
                temperature=0.1,
                stop=["<|end|>", "<|user|>"],
                echo=False
            )
            
            sql_query = response["choices"][0]["text"].strip()
            
            # Extract SQL starting from SELECT (discarding conversational introductions)
            select_idx = sql_query.upper().find("SELECT")
            if select_idx != -1:
                sql_query = sql_query[select_idx:]
                
            # Clean up code blocks if the LLM output wrapped it in ```sql ... ```
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
                
            # Truncate at first semicolon to discard conversational postamble/explanation
            semicolon_idx = sql_query.find(";")
            if semicolon_idx != -1:
                sql_query = sql_query[:semicolon_idx].strip()
                
            # Clean up any trailing backticks or formatting
            sql_query = sql_query.strip().rstrip(";")
            
            print(f"Generated and parsed Dynamic LLM SQL query (Attempt {attempt+1}):\n{sql_query}")
            
            conn = self._get_connection()
            try:
                df = pd.read_sql_query(sql_query, conn)
                conn.close()
                return df, sql_query
            except Exception as e:
                conn.close()
                print(f"Failed to execute LLM SQL query on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    # Append the failed query and error to the prompt for the next iteration
                    prompt += f"{sql_query}<|end|>\n<|user|>\nThe query failed with error: {e}. Please fix the query and provide ONLY the raw corrected SQLite statement.<|end|>\n<|assistant|>\n"
                else:
                    raise e


