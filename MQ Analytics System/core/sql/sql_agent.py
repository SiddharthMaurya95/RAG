# =====================================================
# ✅ SQL GENERATION AGENT
# =====================================================
from core.ollama_client import get_client
from core.config import MODEL_NAME
from core.database import Record

client = get_client()

def generate_sql(query, columns=None):
    """Generates SQLite query based on user request using the unified client."""
    # Dynamically extract database schema context from SQLAlchemy Record mapper
    schema_info_lines = []
    for column in Record.__mapper__.columns:
        nullable_str = "nullable"
        if column.primary_key:
            nullable_str = "PRIMARY KEY, autoincrement"
        elif not column.nullable:
            nullable_str = "not nullable"
        schema_info_lines.append(f"  * {column.key}: {column.type} ({nullable_str})")
    dynamic_schema_context = "\n".join(schema_info_lines)
    
    # Define strict SQL instructions with few-shot examples using the dynamic schema context
    system_prompt = f"""You are a SQLite expert. Given an input question, create only a syntactically correct SQLite query to run. Do not wrap the query in code blocks, do not explain the query, and return ONLY the raw SQL statement.

CRITICAL RULES:
- You MUST query from the 'records' table. The database ONLY contains the 'records' table. Do NOT query from any other table. All data is in the 'records' table!
- Spelling Correction & Column Mapping: If the user misspells column names, uses short forms, or uses slightly different terms, you MUST map them to the correct SQLite column name from the schema below:
  * "custmer", "complaint", "customer complaint" -> customer_complaint
  * "checked", "checked content", "checked contents", "checked_content" -> checked_contents
  * "checked result", "checked results", "checked_result" -> checked_results
  * "repair", "repair content", "repair contents", "repair_content" -> repair_contents
  * "part", "part name", "parts", "causal part", "causal_part_name" -> causal_parts_name
  * "model", "product model" -> product_model_code
  * "sales model" -> sales_model_code
  * "year", "report year" -> report_year
  * "month", "report month" -> report_month
  * "transmission", "transmission number" -> transmission_no
  * "engine", "engine number" -> engine_no
  * "country", "reported country" -> outbreak_country
  * "dealer", "reported company", "company" -> reported_company
- When filtering text columns like 'reported_company', 'outbreak_country', 'causal_parts_name', 'subject', etc., use LIKE '%value%' with LOWER() instead of =. For example, use: LOWER(reported_company) LIKE '%maruti suzuki%' because company names may contain suffixes or extra words like 'MARUTI SUZUKI INDIA LIMITED'.
- For product models, sales models, or trouble codes, if the name/code is partial or generic (e.g. 'YNC', 'YSD', 'ATM', 'ERT', 'P03'), use LIKE 'value%' instead of exact matches. For example, use: product_model_code LIKE 'YNC%', sales_model_code LIKE 'ATM%', or trouble_code_complaint LIKE 'P03%' because actual codes contain suffixes or suffixes/extensions.
- Column names in the 'records' table MUST be spelled exactly as defined in the schema. Be extremely careful with pluralization:
  * Use 'checked_contents' (with an 's') - NEVER use 'checked_content'.
  * Use 'checked_results' (with an 's') - NEVER use 'checked_result'.
  * Use 'causal_parts_name' ('parts' plural, 'name' singular) - NEVER use 'causal_part_name' or 'causal_parts_names'.
- Advanced SQL Analytics: You are allowed and highly encouraged to use advanced SQLite features when necessary, including Common Table Expressions (CTEs), Subqueries, Window Functions (e.g. ROW_NUMBER(), RANK(), DENSE_RANK() OVER (PARTITION BY ... ORDER BY ...)), and Conditional Aggregations (e.g., SUM(CASE WHEN ... THEN 1 ELSE 0 END)).
- LIMIT Clause: CRITICAL: Do NOT set any LIMIT clause in the SQLite query unless a limit is explicitly and literally requested in the user query (e.g., 'top 10', 'limit 5'). Never add LIMIT 10 by default or as a fallback for charts/groupings. If the user asks to compare models or show counts (e.g., "each product_model_code"), you must retrieve all of them without any LIMIT.

The 'records' table has the following database schema dynamically reflected via SQLAlchemy:
{dynamic_schema_context}

Column Descriptions & Content Semantics:
1. Text/Descriptive Columns:
   * subject: Short summary of the technical issue (e.g. "Engine stalling on cold start", "Rear bumper paint peeling").
   * customer_complaint: Detailed complaint text from the customer. Search this column for symptoms, behaviors, or failures.
   * checked_contents: Diagnostic actions taken by the technician.
   * checked_results: Diagnostic findings, trouble codes, or inspection results.
   * repair_contents: Details of the repair actions (e.g. "replaced fuel pump", "repainted").
   * trouble_code_complaint: Diagnostic trouble codes (DTCs) reported by the diagnostic tool (e.g. 'P0300', 'C0035').
   * causal_parts_name: Name of the failed component/part (e.g. "CLUTCH ASSEMBLY", "BUMPER").
   * product_model_code: Product model designation (starts with 'Y').
   * sales_model_code: Sales model designation (starts with letters like 'ATM', 'ERT').
   * segmentation: Major system feature area (e.g. 'Engine', 'Transmission', 'Body').
   * reported_company: Dealership or distributor reporting the issue.
   * outbreak_country: Country where the failure occurred.
   * status: Overall case status (e.g. 'Open', 'Closed').
   * sbpr_no: SBPR report number.
   * ftir_no: FTIR report number.
   * ftir_report_date: Date the report was created (YYYY-MM-DD format).
   * reply_date: Date the reply was submitted.
   * quality: Quality rating ('Good', 'Moderate', 'Poor').

2. Numeric/Quantitative Columns:
   * using_km_int: Cleaner odometer mileage in kilometers. Use this for wear, distance, or wear-related distribution queries.
   * report_year: Calendar year the incident was reported (e.g. 2024, 2025, 2026).
   * report_month: Calendar month the incident was reported (1 to 12).
   * is_resolved: Binary resolution indicator (1 if resolved/fixed, 0 if unresolved). Use to calculate resolution success rates.

Matching Strategy Guidelines:
- If the user query asks about technical symptoms (e.g., stalling, rattling, peeling, leakage, noise), filter using `LIKE` on text columns: `customer_complaint`, `checked_results`, `repair_contents`, or `subject`.
- If the user query specifies a failed component (e.g. "clutch", "engine", "brake"), filter using `LIKE` on `causal_parts_name` or `segmentation`.
- If the user query asks about statistics (e.g., average, total, percentage, rate), use aggregation functions (`AVG`, `COUNT`, `SUM`) on numeric columns (`using_km_int`, `is_resolved`).

Examples:
Input: "Compare failure rates of model YNC412 vs YFG121"
Output: SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE product_model_code IN ('YNC412', 'YFG121') GROUP BY product_model_code;

Input: "Compare YNC and YSD models"
Output: SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE product_model_code LIKE 'YNC%' OR product_model_code LIKE 'YSD%' GROUP BY product_model_code;

Input: "Compare ATM and ERT sales models"
Output: SELECT sales_model_code, COUNT(*) as failure_count FROM records WHERE sales_model_code LIKE 'ATM%' OR sales_model_code LIKE 'ERT%' GROUP BY sales_model_code;

Input: "Compare trouble code frequency for P03 and P04"
Output: SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE trouble_code_complaint LIKE 'P03%' OR trouble_code_complaint LIKE 'P04%' GROUP BY trouble_code_complaint;

Input: "Compare failures in India vs Brunei"
Output: SELECT outbreak_country, COUNT(*) as failure_count FROM records WHERE LOWER(outbreak_country) IN ('india', 'brunei') GROUP BY outbreak_country;

Input: "Show trouble code frequency for model YEC222"
Output: SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE LOWER(product_model_code) = 'yec222' GROUP BY trouble_code_complaint ORDER BY count DESC;

Input: "give me total number of ftir whose report company is maruti suzuki"
Output: SELECT COUNT(*) as count FROM records WHERE LOWER(reported_company) LIKE '%maruti suzuki%';

Input: "Show the top failed part (highest count) for each product model"
Output: WITH ranked_parts AS (SELECT product_model_code, causal_parts_name, COUNT(*) as count, ROW_NUMBER() OVER (PARTITION BY product_model_code ORDER BY COUNT(*) DESC) as rank FROM records WHERE product_model_code IS NOT NULL AND causal_parts_name IS NOT NULL AND causal_parts_name != '' GROUP BY product_model_code, causal_parts_name) SELECT product_model_code, causal_parts_name, count FROM ranked_parts WHERE rank = 1;

Input: "Show total, resolved and resolution rate of failures for each outbreak country"
Output: SELECT outbreak_country, COUNT(*) as total_claims, SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END) as resolved_claims, ROUND(SUM(CASE WHEN is_resolved = 1 THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 1) as resolution_rate FROM records WHERE outbreak_country IS NOT NULL AND outbreak_country != '' GROUP BY outbreak_country ORDER BY total_claims DESC;
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Create a SQLite query to answer: '{query}'"}
    ]
    
    response = client.chat(
        model=MODEL_NAME,
        messages=messages
    )
    
    sql_query = response["message"]["content"].strip()
    
    # Extract SQL starting from SELECT
    select_idx = sql_query.upper().find("SELECT")
    if select_idx != -1:
        sql_query = sql_query[select_idx:]
        
    # Clean up code blocks if present
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
        
    # Truncate at first semicolon
    semicolon_idx = sql_query.find(";")
    if semicolon_idx != -1:
        sql_query = sql_query[:semicolon_idx].strip()
        
    # Remove LLM-generated LIMIT clause if the user query does not explicitly specify a numeric limit
    import re
    limit_match = re.search(r'\bLIMIT\s+(\d+)\b', sql_query, re.IGNORECASE)
    if limit_match:
        q_text_lower = query.lower()
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

    return sql_query.strip().rstrip(";")