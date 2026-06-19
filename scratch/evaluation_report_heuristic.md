# 📊 RAG System Comprehensive Evaluation Report

This report summarizes the performance metrics and results of the Automotive QA Intelligence RAG system, evaluated across core parameters: NLP routing, search retrieval, database SQL generation, response generation quality, and system latencies.

## 📌 Executive Summary

- **Overall Evaluation Date**: 2026-06-15 17:40:47
- **Total Test Duration**: 395.21 seconds
- **Models Evaluated**:
  - Embedding: `all-MiniLM-L6-v2` (SentenceTransformers)
  - Search Vector Store: `FAISS FlatCos IndexIDMap` (6,152 vectors)
  - Local LLM: `Phi-3-mini-4k-instruct-q4` (GGUF via llama-cpp)

---

## 📈 Performance Dashboards

| Metric Parameter | Evaluated Sub-system | Result Metric | Target |
| :--- | :--- | :--- | :--- |
| **NLP Router** | Intent Classification Accuracy | **100.0%** | 90% |
| **NLP Router** | Entity Extraction Accuracy | **100.0%** | 85% |
| **NLP Router** | Filter Parsing Accuracy | **100.0%** | 85% |
| **Vector Retrieval** | Hit Rate @ 1 (Recall@1) | **22.0%** | 70% |
| **Vector Retrieval** | Hit Rate @ 5 (Recall@5) | **50.0%** | 90% |
| **Vector Retrieval** | Mean Reciprocal Rank (MRR@5) | **0.3383** | 0.80 |
| **SQL Generation** | Dynamic Query Execution Success | **100.0%** | 80% |
| **Text Generation** | Groundedness (Faithfulness) Score | **2.00 / 5** | 4.0 |
| **Text Generation** | Answer Relevance Score | **2.70 / 5** | 4.0 |

---

## ⏱️ Latency Analysis

| Pipeline Phase | Average Latency |
| :--- | :--- |
| **NLP Parsing & Classification** | 79.38 ms |
| **Vector Index Retrieval (FAISS)** | 57.30 ms |
| **Dynamic SQL Generation & Exec** | 11299.71 ms |
| **Local LLM Text Generation** | 22576.55 ms |

---

## 🔍 Detailed Component Reports

### 1. NLP Router & Parser
The NLP processor handles classification of the 7 intents and extracts metadata parameters from user inputs.

<details>
<summary><b>View Intent Classification Details</b></summary>

| Query | Expected Intent | Actual Intent | Correct | Latency |
| :--- | :--- | :--- | :--- | :--- |
| "Find all FTIR reports about transmission failure in India" | `SEARCH` | `SEARCH` | ✅ | 963.7 ms |
| "Can you tell me about the problem solver?" | `AMBIGUOUS` | `AMBIGUOUS` | ✅ | 14.1 ms |
| "Show me the top 5 dealers by failure count" | `ANALYTICS` | `ANALYTICS` | ✅ | 15.8 ms |
| "What is the trend of monthly failures for model YHB201?" | `ANALYTICS` | `ANALYTICS` | ✅ | 17.9 ms |
| "Compare the failure rates between product model YHB201 and YHB202" | `COMPARE` | `COMPARE` | ✅ | 19.7 ms |
| "What is the distribution of using mileage before failure?" | `ANALYTICS` | `ANALYTICS` | ✅ | 17.1 ms |
| "Generate the monthly QA report for May 2024" | `REPORT` | `REPORT` | ✅ | 16.0 ms |
| "Show me a chart of the monthly failure trend in 2024" | `VISUALIZE` | `VISUALIZE` | ✅ | 18.1 ms |
| "Explain the chart of trouble code frequency for transmission failures" | `VISUALIZE+EXPLAIN` | `VISUALIZE+EXPLAIN` | ✅ | 15.8 ms |
| "Search for reports in Chile with trouble code P0500" | `SEARCH` | `SEARCH` | ✅ | 16.7 ms |
| "What is the overall repair success rate?" | `ANALYTICS` | `ANALYTICS` | ✅ | 12.6 ms |
| "What are the most common failed parts in YHB201 under 10000 km?" | `ANALYTICS` | `ANALYTICS` | ✅ | 18.6 ms |
| "Compare trouble code frequency for P0500 vs C0035" | `COMPARE` | `COMPARE` | ✅ | 15.9 ms |
| "Find FTIR reports about engine issues for YHB201 in South Africa" | `SEARCH` | `SEARCH` | ✅ | 15.8 ms |
| "Generate monthly report for December 2025" | `REPORT` | `REPORT` | ✅ | 12.9 ms |

</details>

<details>
<summary><b>View Entity Extraction Details</b></summary>

| Query | Expected Entities | Actual Entities | Correct | Extra/Missing |
| :--- | :--- | :--- | :--- | :--- |
| "Find all FTIR reports about transmission failure in India" | `{'COUNTRY': ['India']}` | `{'COUNTRY': ['India']}` | ✅ | None |
| "Can you tell me about the problem solver?" | `{}` | `{}` | ✅ | None |
| "Show me the top 5 dealers by failure count" | `{}` | `{}` | ✅ | None |
| "What is the trend of monthly failures for model YHB201?" | `{'PRODUCT_MODEL': ['YHB201']}` | `{'PRODUCT_MODEL': ['YHB201']}` | ✅ | None |
| "Compare the failure rates between product model YHB201 and YHB202" | `{'PRODUCT_MODEL': ['YHB201', 'YHB202']}` | `{'PRODUCT_MODEL': ['YHB201', 'YHB202']}` | ✅ | None |
| "What is the distribution of using mileage before failure?" | `{}` | `{}` | ✅ | None |
| "Generate the monthly QA report for May 2024" | `{}` | `{}` | ✅ | None |
| "Show me a chart of the monthly failure trend in 2024" | `{}` | `{}` | ✅ | None |
| "Explain the chart of trouble code frequency for transmission failures" | `{}` | `{}` | ✅ | None |
| "Search for reports in Chile with trouble code P0500" | `{'COUNTRY': ['Chile'], 'TROUBLE_CODE': ['P0500']}` | `{'TROUBLE_CODE': ['P0500'], 'COUNTRY': ['Chile']}` | ✅ | None |
| "What is the overall repair success rate?" | `{}` | `{}` | ✅ | None |
| "What are the most common failed parts in YHB201 under 10000 km?" | `{'PRODUCT_MODEL': ['YHB201']}` | `{'PRODUCT_MODEL': ['YHB201']}` | ✅ | None |
| "Compare trouble code frequency for P0500 vs C0035" | `{'TROUBLE_CODE': ['P0500', 'C0035']}` | `{'TROUBLE_CODE': ['P0500', 'C0035']}` | ✅ | None |
| "Find FTIR reports about engine issues for YHB201 in South Africa" | `{'COUNTRY': ['South Africa'], 'PRODUCT_MODEL': ['YHB201']}` | `{'PRODUCT_MODEL': ['YHB201'], 'COUNTRY': ['South Africa']}` | ✅ | None |
| "Generate monthly report for December 2025" | `{}` | `{}` | ✅ | None |

</details>

### 2. Search Retrieval (FAISS)
Evaluated by checking if semantic retrieval can locate the exact ground-truth document inside the 6,152 records when supplied with key details of the incident.
- **Top-1 Hits (Recall@1)**: {retrieval_results['recall_1']:.1f}%
- **Top-3 Hits (Recall@3)**: {retrieval_results['recall_3']:.1f}%
- **Top-5 Hits (Recall@5)**: {retrieval_results['recall_5']:.1f}%
- **Mean Reciprocal Rank (MRR)**: {retrieval_results['mrr_5']:.4f}

### 3. Dynamic SQL Generation (Analytics Engine)
Tests the ability of the local model to draft syntactically correct SQLite statements mapping complex analytical queries directly to database schema aggregations.
- **Dynamic SQL Query Success Rate**: {sql_results['success_rate']:.1f}%

<details>
<summary><b>View SQL Query Execution Log</b></summary>

| User Query | Generated SQL | Success | Rows Returned | Latency |
| :--- | :--- | :--- | :--- | :--- |
| "Compare the failure rates between product model YHB201 and YHB202" | `SELECT product_model_code, COUNT(*) as failure_count FROM records WHERE LOWER(product_model_code) IN ('yhb201', 'yhb202') GROUP BY product_model_code` | ✅ | 1 | 19464.7 ms |
| "Compare failures in Nepal vs South Africa" | `SELECT outbreak_country, COUNT(*) as failure_count FROM records WHERE LOWER(outbreak_country) IN ('nepal', 'south africa') GROUP BY outbreak_country` | ✅ | 2 | 8172.7 ms |
| "Show trouble code frequency for model YHB201" | `SELECT trouble_code_complaint, COUNT(*) as count FROM records WHERE LOWER(product_model_code) = 'yhb201' GROUP BY trouble_code_complaint ORDER BY count DESC LIMIT 10` | ✅ | 10 | 10290.5 ms |
| "give me total number of ftir whose reported company is Maruti Suzuki" | `SELECT COUNT(*) as count FROM records WHERE LOWER(reported_company) LIKE '%maruti suzuki%'` | ✅ | 1 | 7088.4 ms |
| "Show the average mileage (using_km_int) of resolved failures in Nepal" | `SELECT AVG(using_km_int) as average_mileage FROM records WHERE LOWER(outbreak_country) = 'nepal' AND is_resolved = 1` | ✅ | 1 | 8847.2 ms |
| "List the top 5 causal parts for transmission issues in 2024" | `SELECT causal_parts_name, COUNT(*) as count FROM records WHERE LOWER(segmentation) LIKE '%transmission%' AND report_year = 2024 GROUP BY causal_parts_name ORDER BY count DESC LIMIT 5` | ✅ | 0 | 11347.5 ms |
| "How many failures occurred in South Africa for model YHB202 in 2024?" | `SELECT COUNT(*) as failure_count FROM records WHERE LOWER(outbreak_country) = 'south africa' AND LOWER(product_model_code) = 'yhb202' AND report_year = 2024` | ✅ | 1 | 11290.6 ms |
| "What is the average mileage before failure for YHB201?" | `SELECT AVG(using_km_int) as average_mileage FROM records WHERE LOWER(product_model_code) = 'yhb201' AND using_km_int > 0` | ✅ | 1 | 9409.4 ms |
| "What are the most common failed parts in transmission under 30000 km?" | `SELECT causal_parts_name, COUNT(*) as count FROM records WHERE using_km_int < 30000 AND segmentation = 'Transmission' GROUP BY causal_parts_name ORDER BY count DESC LIMIT 10` | ✅ | 10 | 14325.0 ms |
| "What is the resolution rate of failures with trouble code P0500?" | `SELECT SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END) AS resolved_count, COUNT(*) AS total_failures FROM records WHERE trouble_code_complaint LIKE '%P0500%'` | ✅ | 1 | 12761.0 ms |

</details>

### 4. Text Generation (LLM-as-a-Judge)
Scores the final output of the assistant using the local model as a double-blind evaluator of Faithfulness and Answer Relevance.
- **Groundedness (Faithfulness)**: {generation_results['avg_faithfulness']:.2f} / 5
- **Answer Relevance**: {generation_results['avg_relevance']:.2f} / 5

<details>
<summary><b>View Generation QA Evaluations</b></summary>

#### Case 1: "Find all FTIR reports about transmission failure in India"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: GEARBOX OIL LEAKAGE FROM TRANSMISSION SIDE | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 2: oil leakage | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 3: Electrical fault | Suzuki Workshop Mumbai | India
Case 4: GEAR NOT SHIFTING | MARUTI SUZUKI IND...
  ```
- **Generated Answer**:
  > There are exactly 107 matching cases in the database for FTIR reports about transmission failure in India. The top 5 most relevant sample cases are as follows:

1. **Case 1 (FTIR IN202606B04947)**: GEARBOX OIL LEAKAGE FROM TRANSMISSION SIDE, repaired by technician.
2. **Case 4 (FTIR IN202606B01287)**: GEAR NOT SHIFTING, repaired by technician.
3. **Case 5 (FTIR IN202606B02978)**: TIMING CHAIN COVER ABNORMAL OIL LEAK APPEARANCE, repaired by technician.

For a complete list, please refer to the full database.
- **Scoring**: Faithfulness = **1/5** | Relevance = **3/5**
- **Total Latency**: 40386.7 ms

---
#### Case 2: "Search for reports in Chile with trouble code P0500"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: AC issue | Suzuki Workshop Mumbai | Nepal
Case 2: Electrical fault | Maruti Arena Delhi | Nepal
Case 3: Engine problem | Maruti Arena Delhi | Saudi Arabia
Case 4: MIL warning light glowing, DTC P0500 Vehicle Speed Sensor Malfunction showing c...
  ```
- **Generated Answer**:
  > There are exactly 181 matching cases in the database for reports in Chile with trouble code P0500. The top sample case relevant to your query is from FTIR/2024/1241, where a vehicle in Chile had a DTC P0500 (Vehicle Speed Sensor Malfunction) and the technician action was to replace the transmission solenoid valve assembly.
- **Scoring**: Faithfulness = **1/5** | Relevance = **3/5**
- **Total Latency**: 20762.6 ms

---
#### Case 3: "Find FTIR reports about engine issues for YHB201 in South Africa"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: Problem in vehicle | Suzuki Workshop Mumbai | South Africa
Case 2: Noise problem | Maruti Arena Delhi | South Africa
Case 3: Battery drain complaint, DTC P0441 Evaporative Emission Control System Incorrect Purge Flow, vehicle not starting aft...
  ```
- **Generated Answer**:
  > There are exactly 5 matching cases in the database for FTIR reports about engine issues for YHB201 in South Africa. However, the provided cases do not specifically mention engine issues or the YHB201 model or South Africa. Therefore, based on the given information, the exact count of 5 cases is the total matching the query, but no specific details about engine issues for YHB201 in South Africa are available from these cases.
- **Scoring**: Faithfulness = **3/5** | Relevance = **3/5**
- **Total Latency**: 23359.7 ms

---
#### Case 4: "Show me FTIR reports involving fuel system problem"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: vehicle report with compliant of fuel level not showing in meter | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 2: FUEL INDICATOR NOT WORKING | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 3: vehicle report with compliant of fuel level not showing in...
  ```
- **Generated Answer**:
  > There are exactly 1220 FTIR reports involving fuel system problems in the database. The top 5 most relevant sample cases are as follows:

1. (FTIR IN202506B02815) - Issue: Fuel level not showing in meter, related to unit assembly, navy box.
2. (FTIR IN202606B04519) - Issue: Fuel indicator not working, related to compressor assembly.
3. (FTIR IN202506B01642) - Issue: Fuel level not showing in meter, related to unit assembly, navy box.
4. (FTIR SA202506B01199) - Issue: Fuel indicator not working, related to compressor assembly.
5. (FTIR IN202406B02730) - Issue: Fuel level not showing in meter, related to end strg tie rod.
- **Scoring**: Faithfulness = **1/5** | Relevance = **3/5**
- **Total Latency**: 46318.4 ms

---
#### Case 5: "Lookup incident in India with trouble code C0035"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: C0035 | Suzuki Workshop Mumbai | India
Case 2: C0035 | Arena Hyderabad | India
Case 3: Battery drain complaint, DTC C0035 Right Front Wheel Speed Sensor Circuit, vehicle not starting after 2 days parking, electrical system abnormality | True ...
  ```
- **Generated Answer**:
  > There are exactly 7 matching cases in the database for incidents in India with trouble code C0035. The top 5 cases provided do not specify the location. To provide the exact incidents in India, a detailed review of all 7 cases is required.
- **Scoring**: Faithfulness = **3/5** | Relevance = **3/5**
- **Total Latency**: 15567.3 ms

---
#### Case 6: "Find incidents related to brake pads wear in UK"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: tuk tuk noise while brake pedal release | BOUSTEAD SDN BHD | BRUNEI
Case 2: tuk tuk noise while brake pedal release | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 3: hand brake light in cluster meter | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 4: ...
  ```
- **Generated Answer**:
  > There are exactly 329 matching cases in the database for incidents related to brake pads wear in the UK. The provided sample cases do not match this query.
- **Scoring**: Faithfulness = **1/5** | Relevance = **2/5**
- **Total Latency**: 10528.2 ms

---
#### Case 7: "Find trouble code complaints in South Africa for model YHB202"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: Customer complaint | True Value Bangalore | South Africa
Case 2: Customer complaint | Arena Hyderabad | South Africa
Case 3: Customer complaint | Nexa Motors Gurgaon | South Africa
Case 4: Customer complaint | Arena Hyderabad | South Africa
C...
  ```
- **Generated Answer**:
  > There are exactly 3208 matching cases in the database for trouble code complaints in South Africa for model YHB202. The sample cases provided do not specify trouble codes or the model YHB202, so the exact count cannot be determined from the given information.
- **Scoring**: Faithfulness = **3/5** | Relevance = **2/5**
- **Total Latency**: 15936.1 ms

---
#### Case 8: "Lookup reports with causal part wheel bearing"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: noise from front side due to part failure both arm assy | MARUTI SUZUKI INDIA LIMITED | INDIA
Case 2: noise from front side due to part failure both arm assy | BAMORYS LIMITED | LIBYA
Case 3: FRONT SIDE NOISE AND VIBRATION FRONT RH SIDE WHEEL...
  ```
- **Generated Answer**:
  > There are exactly 6152 matching cases in the database for reports with causal part wheel bearing. The top sample case is:
Case 3 (FTIR IN202606B01630): Issue reported was 'FRONT SIDE NOISE AND VIBRATION FRONT RH SIDE WHEEL BEARING NOISE', related to causal part bearingfront wheel. Checked results found 'inspected by technician', and technician action was 'repaired'.
- **Scoring**: Faithfulness = **2/5** | Relevance = **3/5**
- **Total Latency**: 24449.8 ms

---
#### Case 9: "Search reports about poor cabin heating in Sweden"
- **Retrieved Context Context (Sample)**:
  ```text
  ...
  ```
- **Generated Answer**:
  > I don't have access to specific FTIR or FPCR reports. However, based on your query, I would recommend searching for reports related to cabin heating issues in Sweden within the Field Technical Information Report (FTIR) or Field Problem Counter Report (FPCR) databases. If you provide a specific record number or more details, I can assist further.
- **Scoring**: Faithfulness = **2/5** | Relevance = **2/5**
- **Total Latency**: 17980.5 ms

---
#### Case 10: "Find engine stalling cases under 10000 km in India"
- **Retrieved Context Context (Sample)**:
  ```text
  Case 1: Battery drain complaint, DTC C0035 Right Front Wheel Speed Sensor Circuit, vehicle not starting after 2 days parking, electrical system abnormality | True Value Bangalore | India...
  ```
- **Generated Answer**:
  > There are exactly 1 matching case in the database for engine stalling issues under 10000 km in India. However, the provided case does not specifically address engine stalling. It deals with a battery drain complaint and related electrical issues.
- **Scoring**: Faithfulness = **3/5** | Relevance = **3/5**
- **Total Latency**: 12893.1 ms

---

</details>
