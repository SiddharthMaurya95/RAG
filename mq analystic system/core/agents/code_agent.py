from core.ollama_client import get_client
from core.config import MODEL_NAME
from core.engine.intent.intent_classifier import Intent_classification

client = get_client()


def generate_code(query, columns):

    # =====================================================
    # ✅ STEP 1: GET INTENT / KPI / FILTERS / AGGREGATIONS
    # =====================================================
    intent_engine = Intent_classification()

    intents, kpis, filters, aggregations = intent_engine.build_intent_prompt(
        base_instructions="FTIR dataset analysis",
        question=query
    )

    # ✅ Build structured understanding
    intent_text = f"""
        Intents: {', '.join([str(i) for i in intents]) if intents else 'None'}
        KPIs: {', '.join([str(k) for k in kpis]) if kpis else 'None'}
        Filters: {', '.join([str(f) for f in filters]) if filters else 'None'}
        Aggregations: {', '.join([str(a) for a in aggregations]) if aggregations else 'None'}
    """

    # =====================================================
    # ✅ STEP 2: ENHANCED PROMPT (IMPORTANT CHANGE)
    # =====================================================
    prompt = f"""
You are a STRICT Python data analyst.

Your task is to write executable Python code for EDA using a pandas DataFrame named df.

========================================
DATASET CONTEXT
========================================
This dataset represents FTIR (First Technical Information Report) data.
Includes segmentation, causal parts, issues, VIN, dealer, country, and repair information.

Columns:
{list(columns)}


Column Meanings (sample – use for better understanding):
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

========================================
UNDERSTOOD USER INTENT (IMPORTANT)
========================================
{intent_text}

Use the above structured understanding to guide your logic:
- Apply filters BEFORE aggregation
- Use KPIs to decide metrics (count, avg, sum, etc.)
- Use aggregations for grouping
- Use intents to decide analysis type (trend, ranking, etc.)

========================================
CRITICAL RULES (DO NOT BREAK)
========================================

1. OUTPUT FORMAT:
- Output ONLY Python code
- MUST be inside ONE ```python``` block

2. DATA USAGE:
- df is ALREADY AVAILABLE
- DO NOT use pd.read_csv()
- DO NOT load any file

3. RESULT VARIABLE:
- ALWAYS assign final output to variable 'result'
- 'result' MUST contain actual data (DataFrame or Series)
- NEVER overwrite result with string
- NEVER assign result = plt

4. PLOTTING RULES:
- Use matplotlib only
- If plot is required:
    - Use result for plotting
    - Add xlabel, ylabel, title
    - Call plt.show()

5. CODE QUALITY:
- Must be COMPLETE and EXECUTABLE
- NO syntax errors

6. FALLBACK:
result = "Sorry, out of scope"

========================================
USER QUERY
========================================
{query}

========================================
OUTPUT (STRICT)
========================================
```python
# ONLY VALID PYTHON CODE HERE
    """
# =====================================================
# ✅ STEP 3: CALL MODEL
# =====================================================
    response = client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]








# from core.ollama_client import get_client
# from core.config import MODEL_NAME

# client = get_client()

# def generate_code(query, columns):


#     prompt = f"""
#     You are a STRICT Python data analyst.

#     Your task is to write executable Python code for EDA using a pandas DataFrame named df.

#     ========================================
#     DATASET CONTEXT
#     ========================================
#     This dataset represents FTIR (First Technical Information Report) data.
#     Includes segmentation, causal parts, issues, VIN, dealer, country, and repair information.

#     Columns:
#     {list(columns)}

#     Column Meanings ( use for better understanding):
#     SBPR No.: Service/Field problem report unique ID
#     FTIR No.: Field Technical Investigation Report number
#     Causal Parts Name (English): Name of faulty part
#     Product Model Code: Internal product/model identifier
#     Sales Model Code: Sales model identifier for market
#     Segmentation: Vehicle/category classification
#     Subject (English): Issue description or problem summary
#     Causal Parts No.: Part number causing the issue
#     Rank: Severity or priority ranking of issue
#     Reported Country: Country where issue was reported
#     VIN: Vehicle Identification Number
#     Report Company: Company reporting the issue
#     Issued Company: Company issuing the report
#     FTIR Report Date: Date when report was created
#     Reply Date: Response date to the report
#     Status: Current state of report (open/closed/etc.)
#     FC-OK: Manufacturing Date of the Vehicle
#     Date Registered: Date vehicle was registered
#     Date of Incident: When issue occurred
#     Mileage / Using Time: Mileage Usage at time of issue
#     Days Used: Number of days vehicle used before issue
#     FPCR No.: Field Problem Correction Report number
#     Engine No.: Engine identifier
#     Transmission No.: Transmission identifier
#     Outbreak Country: Country where defect originated
#     Sales Dealer: Dealer who sold vehicle
#     Service Dealer: Dealer who serviced vehicle
#     Spec on Destination: Regional specification of vehicle
#     Collection Request Date: Date when part collection requested
#     Parts Retrieved Date: Date when defective part collected
#     Manufacturer Factory: Manufacturing plant
#     Person of Action Judgement: Individual making decision
#     Department of Action Judgement: Department responsible
#     Judgement Date: Decision date
#     Action Judgement: Decision taken (repair/replace/etc.)
#     Reason of "Not to File as an SBPR": Justification for exclusion
#     Approval Judgement Date: Final approval date

#     ========================================
#     CRITICAL RULES (DO NOT BREAK)
#     ========================================

#     1. OUTPUT FORMAT:
#     - Output ONLY Python code
#     - MUST be inside ONE ```python``` block
#     - NO explanation, NO text, NO comments outside code

#     2. DATA USAGE:
#     - df is ALREADY AVAILABLE
#     - DO NOT use pd.read_csv()
#     - DO NOT load any file

#     3. RESULT VARIABLE:
#     - ALWAYS assign final output to variable 'result'
#     - 'result' MUST contain actual data (DataFrame or Series)
#     - NEVER overwrite result with string
#     - NEVER assign result = plt

#     4. PLOTTING RULES:
#     - Use matplotlib only
#     - If plot is required:
#         - Use result for plotting
#         - Add xlabel, ylabel, title
#         - Call plt.show()

#     5. CODE QUALITY:
#     - Must be COMPLETE and EXECUTABLE
#     - NO placeholders
#     - NO syntax errors

#     6. FALLBACK:
#     - If query is not possible:
#         result = "Sorry, out of scope"

#     ========================================
#     IMPORTANT PATTERN (FOLLOW THIS)
#     ========================================

#     If analysis involves aggregation:

#     Example:
#     result = df['column'].value_counts().head(10)

#     # Then plot
#     result.plot(kind='bar')
#     plt.xlabel(...)
#     plt.ylabel(...)
#     plt.title(...)
#     plt.show()

#     ========================================
#     USER QUERY
#     ========================================
#     {query}

#     ========================================
#     OUTPUT (STRICT)
#     ========================================
#     ```python
#     # ONLY VALID PYTHON CODE HERE
#     ``
        
# #   prompt = f"""


#     response = client.chat(
#         model=MODEL_NAME,
#         messages=[{"role": "user", "content": prompt}]
#     )

#     return response["message"]["content"]