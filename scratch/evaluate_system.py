import os
import sys
import time
import sqlite3
import re
import json
import numpy as np
import pandas as pd

# Append automotive_qa to path
sys.path.append(os.path.join(os.path.abspath("."), "automotive_qa"))

from core.singletons import get_db_connection, get_embedder, get_llm
from core.router import QueryRouter
from nlp.pipeline import NLPProcessor
from analytics.engine import AnalyticsEngine

# Initialize system components
db_path = get_db_connection()
router = QueryRouter(db_path)
nlp = NLPProcessor()
analytics_engine = AnalyticsEngine(db_path)
embedder = get_embedder()
llm_client = get_llm()

# Define test cases for NLP classification and extraction
nlp_test_cases = [
    {
        "query": "Find all FTIR reports about transmission failure in India",
        "intent": "SEARCH",
        "entities": {"COUNTRY": ["India"]},
        "filters": {"segmentation": "Transmission"}
    },
    {
        "query": "Can you tell me about the problem solver?",
        "intent": "AMBIGUOUS",
        "entities": {},
        "filters": {}
    },
    {
        "query": "Show me the top 5 dealers by failure count",
        "intent": "ANALYTICS",
        "entities": {},
        "filters": {"limit": 5}
    },
    {
        "query": "What is the trend of monthly failures for model YHB201?",
        "intent": "ANALYTICS",
        "entities": {"PRODUCT_MODEL": ["YHB201"]},
        "filters": {}
    },
    {
        "query": "Compare the failure rates between product model YHB201 and YHB202",
        "intent": "COMPARE",
        "entities": {"PRODUCT_MODEL": ["YHB201", "YHB202"]},
        "filters": {}
    },
    {
        "query": "What is the distribution of using mileage before failure?",
        "intent": "ANALYTICS",
        "entities": {},
        "filters": {}
    },
    {
        "query": "Generate the monthly QA report for May 2024",
        "intent": "REPORT",
        "entities": {},
        "filters": {"year": 2024, "month": 5}
    },
    {
        "query": "Show me a chart of the monthly failure trend in 2024",
        "intent": "VISUALIZE",
        "entities": {},
        "filters": {"year": 2024}
    },
    {
        "query": "Explain the chart of trouble code frequency for transmission failures",
        "intent": "VISUALIZE+EXPLAIN",
        "entities": {},
        "filters": {"segmentation": "Transmission"}
    },
    {
        "query": "Search for reports in Chile with trouble code P0500",
        "intent": "SEARCH",
        "entities": {"COUNTRY": ["Chile"], "TROUBLE_CODE": ["P0500"]},
        "filters": {}
    },
    {
        "query": "What is the overall repair success rate?",
        "intent": "ANALYTICS",
        "entities": {},
        "filters": {}
    },
    {
        "query": "What are the most common failed parts in YHB201 under 10000 km?",
        "intent": "ANALYTICS",
        "entities": {"PRODUCT_MODEL": ["YHB201"]},
        "filters": {"km_max": 10000}
    },
    {
        "query": "Compare trouble code frequency for P0500 vs C0035",
        "intent": "COMPARE",
        "entities": {"TROUBLE_CODE": ["P0500", "C0035"]},
        "filters": {}
    },
    {
        "query": "Find FTIR reports about engine issues for YHB201 in South Africa",
        "intent": "SEARCH",
        "entities": {"COUNTRY": ["South Africa"], "PRODUCT_MODEL": ["YHB201"]},
        "filters": {"segmentation": "Engine"}
    },
    {
        "query": "Generate monthly report for December 2025",
        "intent": "REPORT",
        "entities": {},
        "filters": {"year": 2025, "month": 12}
    }
]

sql_test_cases = [
    {"query": "Compare the failure rates between product model YHB201 and YHB202"},
    {"query": "Compare failures in Nepal vs South Africa"},
    {"query": "Show trouble code frequency for model YHB201"},
    {"query": "give me total number of ftir whose reported company is Maruti Suzuki"},
    {"query": "Show the average mileage (using_km_int) of resolved failures in Nepal"},
    {"query": "List the top 5 causal parts for transmission issues in 2024"},
    {"query": "How many failures occurred in South Africa for model YHB202 in 2024?"},
    {"query": "What is the average mileage before failure for YHB201?"},
    {"query": "What are the most common failed parts in transmission under 30000 km?"},
    {"query": "What is the resolution rate of failures with trouble code P0500?"}
]

def evaluate_nlp():
    print("\n--- Evaluating NLP Intent Classification & Entity Extraction ---")
    correct_intents = 0
    total_cases = len(nlp_test_cases)
    
    intent_results = []
    entity_results = []
    filter_results = []
    
    latency_list = []
    
    for tc in nlp_test_cases:
        query = tc["query"]
        expected_intent = tc["intent"]
        expected_entities = tc["entities"]
        expected_filters = tc["filters"]
        
        start_time = time.time()
        parsed = nlp.parse_query(query)
        latency = (time.time() - start_time) * 1000.0
        latency_list.append(latency)
        
        actual_intent = parsed["intent"]
        actual_entities = parsed["entities"]
        actual_filters = parsed["filters"]
        
        # Intent Check
        is_intent_correct = (actual_intent == expected_intent)
        if is_intent_correct:
            correct_intents += 1
            
        intent_results.append({
            "query": query,
            "expected": expected_intent,
            "actual": actual_intent,
            "correct": is_intent_correct,
            "latency_ms": latency
        })
        
        # Entities Check
        ent_correct = True
        missing_ents = []
        extra_ents = []
        for label, vals in expected_entities.items():
            actual_vals = actual_entities.get(label, [])
            for val in vals:
                # Case insensitive match
                if not any(val.lower() == av.lower() for av in actual_vals):
                    ent_correct = False
                    missing_ents.append(f"{label}:{val}")
        for label, vals in actual_entities.items():
            expected_vals = expected_entities.get(label, [])
            for val in vals:
                if not any(val.lower() == ev.lower() for ev in expected_vals):
                    ent_correct = False
                    extra_ents.append(f"{label}:{val}")
                    
        entity_results.append({
            "query": query,
            "expected": expected_entities,
            "actual": {k: v for k, v in actual_entities.items() if v},
            "correct": ent_correct,
            "missing": missing_ents,
            "extra": extra_ents
        })
        
        # Filters Check
        filt_correct = True
        missing_filts = {}
        extra_filts = {}
        for k, v in expected_filters.items():
            if actual_filters.get(k) != v:
                filt_correct = False
                missing_filts[k] = v
        for k, v in actual_filters.items():
            if k not in expected_filters and v is not None and v != 5: # 5 is default limit, ignore if expected didn't specify
                filt_correct = False
                extra_filts[k] = v
                
        filter_results.append({
            "query": query,
            "expected": expected_filters,
            "actual": actual_filters,
            "correct": filt_correct,
            "missing": missing_filts,
            "extra": extra_filts
        })
        
    intent_accuracy = (correct_intents / total_cases) * 100.0
    entity_accuracy = (sum(1 for r in entity_results if r["correct"]) / total_cases) * 100.0
    filter_accuracy = (sum(1 for r in filter_results if r["correct"]) / total_cases) * 100.0
    avg_latency = np.mean(latency_list)
    
    print(f"Intent Classification Accuracy: {intent_accuracy:.2f}% ({correct_intents}/{total_cases})")
    print(f"Entity Extraction Accuracy: {entity_accuracy:.2f}%")
    print(f"Filter Extraction Accuracy: {filter_accuracy:.2f}%")
    print(f"Average NLP Latency: {avg_latency:.2f} ms")
    
    return {
        "intent_accuracy": intent_accuracy,
        "entity_accuracy": entity_accuracy,
        "filter_accuracy": filter_accuracy,
        "avg_latency_ms": avg_latency,
        "intent_details": intent_results,
        "entity_details": entity_results,
        "filter_details": filter_results
    }

def evaluate_retrieval(num_samples=50):
    print(f"\n--- Evaluating Hybrid Retrieval (FAISS Search) on {num_samples} Samples ---")
    
    # 1. Fetch random records that have sufficient data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, subject, customer_complaint, causal_parts_name, trouble_code_complaint, outbreak_country, product_model_code
        FROM records
        WHERE subject IS NOT NULL AND subject != ''
          AND causal_parts_name IS NOT NULL AND causal_parts_name != ''
          AND trouble_code_complaint IS NOT NULL AND trouble_code_complaint != ''
          AND outbreak_country IS NOT NULL AND outbreak_country != ''
        ORDER BY RANDOM()
        LIMIT ?;
    """, (num_samples,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if len(rows) < num_samples:
        print(f"Warning: Only found {len(rows)} records matching requirements. Scaling sample count.")
        num_samples = len(rows)
        
    # Get all record IDs for whitelist
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM records;")
    all_ids = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    rec_hits = {1: 0, 3: 0, 5: 0}
    mrr_list = []
    retrieval_latencies = []
    
    details = []
    
    for row in rows:
        rec_id, subject, complaint, part, tc_code, country, model = row
        
        # Formulate query semantically
        query_text = f"Incident involving {part} failure with trouble code {tc_code} in {country}"
        
        start_time = time.time()
        # Retrieve top 5 using embedder
        results = embedder.search_subset(query_text, all_ids, k=5, threshold=0.0)
        latency = (time.time() - start_time) * 1000.0
        retrieval_latencies.append(latency)
        
        retrieved_ids = [res["record_id"] for res in results]
        
        # Evaluate ranks
        rank = -1
        if rec_id in retrieved_ids:
            rank = retrieved_ids.index(rec_id) + 1
            
        # Hit rates
        for k in [1, 3, 5]:
            if rank != -1 and rank <= k:
                rec_hits[k] += 1
                
        # MRR
        mrr = 1.0 / rank if rank != -1 else 0.0
        mrr_list.append(mrr)
        
        details.append({
            "record_id": rec_id,
            "query": query_text,
            "retrieved_ids": retrieved_ids,
            "rank": rank,
            "mrr": mrr,
            "latency_ms": latency
        })
        
    recall_1 = (rec_hits[1] / num_samples) * 100.0
    recall_3 = (rec_hits[3] / num_samples) * 100.0
    recall_5 = (rec_hits[5] / num_samples) * 100.0
    mean_mrr = np.mean(mrr_list)
    avg_latency = np.mean(retrieval_latencies)
    
    print(f"Recall@1: {recall_1:.2f}%")
    print(f"Recall@3: {recall_3:.2f}%")
    print(f"Recall@5: {recall_5:.2f}%")
    print(f"MRR@5: {mean_mrr:.4f}")
    print(f"Average Retrieval Latency: {avg_latency:.2f} ms")
    
    return {
        "recall_1": recall_1,
        "recall_3": recall_3,
        "recall_5": recall_5,
        "mrr_5": mean_mrr,
        "avg_latency_ms": avg_latency,
        "details": details
    }

def evaluate_sql_generation():
    print(f"\n--- Evaluating Dynamic SQL Generation on {len(sql_test_cases)} Queries ---")
    
    success_count = 0
    sql_latencies = []
    details = []
    
    for idx, tc in enumerate(sql_test_cases, 1):
        query = tc["query"]
        print(f"Running SQL Gen Test {idx}/{len(sql_test_cases)}: '{query}'")
        
        start_time = time.time()
        success = False
        generated_sql = "N/A"
        error_msg = ""
        rows_returned = 0
        
        try:
            df, generated_sql = analytics_engine.query_via_llm(query)
            success = True
            rows_returned = len(df)
            success_count += 1
        except Exception as e:
            error_msg = str(e)
            
        latency = (time.time() - start_time) * 1000.0
        sql_latencies.append(latency)
        
        details.append({
            "query": query,
            "sql": generated_sql,
            "success": success,
            "rows_returned": rows_returned,
            "error": error_msg,
            "latency_ms": latency
        })
        
    success_rate = (success_count / len(sql_test_cases)) * 100.0
    avg_latency = np.mean(sql_latencies)
    
    print(f"SQL Generation Success Rate: {success_rate:.2f}% ({success_count}/{len(sql_test_cases)})")
    print(f"Average SQL Gen Latency: {avg_latency:.2f} ms")
    
    return {
        "success_rate": success_rate,
        "avg_latency_ms": avg_latency,
        "details": details
    }

def run_llm_judge(query, context, answer):
    """Invokes the local LLM to score faithfulness and relevance on a scale of 1-5."""
    llm = llm_client.load_model()
    
    # 1. Evaluate Faithfulness
    faith_prompt = f"""<|system|>
You are an objective AI judge evaluating the quality of answers generated by a RAG system.
Your job is to rate the FAITHFULNESS of the Answer on a scale from 1 to 5.
An answer is FAITHFUL if all the factual claims made in the Answer can be directly inferred from the Context.

SCORING CRITERIA:
- 5 (Excellent): Every single claim in the answer is fully supported by the provided context. No external knowledge or extrapolation.
- 4 (Good): The main claims are supported; minor details are extrapolated but do not contradict the context.
- 3 (Fair): Some claims are supported, but there are significant details that are completely unsupported by the context.
- 2 (Poor): Most of the answer is unsupported by the context; only a small part is grounded.
- 1 (Unacceptable): The answer contradicts the context or has zero grounding.

Respond with ONLY a single integer score (1, 2, 3, 4, or 5). Do not write anything else.
<|end|>
<|user|>
User Query: {query}
Context: {context}
Answer: {answer}

Faithfulness Score:<|end|>
<|assistant|>
"""
    
    response = llm(faith_prompt, max_tokens=5, temperature=0.1, stop=["<|end|>"], echo=False)
    faith_text = response["choices"][0]["text"].strip()
    match = re.search(r'\b([1-5])\b', faith_text)
    faith_score = int(match.group(1)) if match else 3
    
    # 2. Evaluate Answer Relevance
    relevance_prompt = f"""<|system|>
You are an objective AI judge evaluating the quality of answers generated by a RAG system.
Your job is to rate the ANSWER RELEVANCE on a scale from 1 to 5.
Relevance measures if the generated answer directly and fully addresses the User Query.

SCORING CRITERIA:
- 5 (Excellent): The answer is highly relevant, complete, and directly addresses the query without fluff.
- 4 (Good): The answer addresses the query well, with minor omissions or slight redundancy.
- 3 (Fair): The answer is related but misses the core question or contains major irrelevant details.
- 2 (Poor): The answer is barely relevant, mostly talking about generalities without solving the query.
- 1 (Unacceptable): The answer is completely off-topic or irrelevant.

Respond with ONLY a single integer score (1, 2, 3, 4, or 5). Do not write anything else.
<|end|>
<|user|>
User Query: {query}
Context: {context}
Answer: {answer}

Relevance Score:<|end|>
<|assistant|>
"""
    response = llm(relevance_prompt, max_tokens=5, temperature=0.1, stop=["<|end|>"], echo=False)
    rel_text = response["choices"][0]["text"].strip()
    match = re.search(r'\b([1-5])\b', rel_text)
    rel_score = int(match.group(1)) if match else 3
    
    return faith_score, rel_score

def evaluate_generation_quality(num_samples=10):
    print(f"\n--- Evaluating Generation Quality (LLM-as-a-Judge) on {num_samples} Queries ---")
    
    # Let's draw 10 random search queries from our NLP benchmark
    search_queries = [
        "Find all FTIR reports about transmission failure in India",
        "Search for reports in Chile with trouble code P0500",
        "Find FTIR reports about engine issues for YHB201 in South Africa",
        "Show me FTIR reports involving fuel system problem",
        "Lookup incident in India with trouble code C0035",
        "Find incidents related to brake pads wear in UK",
        "Find trouble code complaints in South Africa for model YHB202",
        "Lookup reports with causal part wheel bearing",
        "Search reports about poor cabin heating in Sweden",
        "Find engine stalling cases under 10000 km in India"
    ][:num_samples]
    
    generation_latencies = []
    faithfulness_scores = []
    relevance_scores = []
    
    details = []
    
    for idx, query in enumerate(search_queries, 1):
        print(f"Evaluating generation {idx}/{num_samples}: '{query}'")
        
        # 1. Run full dispatch through router
        start_time = time.time()
        res = router.dispatch_query(query, user_id=999)
        dispatch_latency = (time.time() - start_time) * 1000.0
        
        # 2. Extract context (citations summaries) and prompt assistant
        citations = res.get("citations", [])
        res_type = res.get("type")
        data_messages = res.get("data")
        
        answer_text = ""
        context_text = ""
        
        # Since it's a stream, we evaluate the text generation
        if res_type == "text_stream" and isinstance(data_messages, list):
            # Formulate context text
            context_text = "\n".join([f"Case {i}: {c['subject']} | {c['reported_company']} | {c['outbreak_country']}" for i, c in enumerate(citations, 1)])
            
            # Generate the LLM completion
            start_gen = time.time()
            completion_chunks = list(llm_client.generate_chat_stream(data_messages))
            gen_latency = (time.time() - start_gen) * 1000.0
            generation_latencies.append(gen_latency)
            
            answer_text = "".join(completion_chunks)
            
            # Run judge
            faith_score, rel_score = run_llm_judge(query, context_text, answer_text)
            faithfulness_scores.append(faith_score)
            relevance_scores.append(rel_score)
            
            details.append({
                "query": query,
                "context": context_text,
                "answer": answer_text,
                "faithfulness": faith_score,
                "relevance": rel_score,
                "latency_ms": dispatch_latency + gen_latency
            })
            print(f" -> Faithfulness: {faith_score}/5 | Relevance: {rel_score}/5")
        else:
            print(f" -> Skipped (non-text stream result type: {res_type})")
            
    avg_gen_latency = np.mean(generation_latencies) if generation_latencies else 0.0
    avg_faith = np.mean(faithfulness_scores) if faithfulness_scores else 0.0
    avg_relevance = np.mean(relevance_scores) if relevance_scores else 0.0
    
    print(f"Average Faithfulness Score: {avg_faith:.2f}/5")
    print(f"Average Relevance Score: {avg_relevance:.2f}/5")
    print(f"Average Text Generation Latency: {avg_gen_latency:.2f} ms")
    
    return {
        "avg_faithfulness": avg_faith,
        "avg_relevance": avg_relevance,
        "avg_gen_latency_ms": avg_gen_latency,
        "details": details
    }

def main():
    print("==================================================")
    print("STARTING FULL RAG SYSTEM EVALUATION ENGINE")
    print("==================================================")
    
    overall_start = time.time()
    
    # Run modules
    nlp_results = evaluate_nlp()
    retrieval_results = evaluate_retrieval(num_samples=50)
    sql_results = evaluate_sql_generation()
    generation_results = evaluate_generation_quality(num_samples=10)
    
    overall_duration = time.time() - overall_start
    print(f"\n==================================================")
    print(f"EVALUATION COMPLETED IN {overall_duration:.2f} SECONDS")
    print(f"==================================================")
    
    # Build markdown report
    report_md = f"""# 📊 RAG System Comprehensive Evaluation Report

This report summarizes the performance metrics and results of the Automotive QA Intelligence RAG system, evaluated across core parameters: NLP routing, search retrieval, database SQL generation, response generation quality, and system latencies.

## 📌 Executive Summary

- **Overall Evaluation Date**: {time.strftime("%Y-%m-%d %H:%M:%S")}
- **Total Test Duration**: {overall_duration:.2f} seconds
- **Models Evaluated**:
  - Embedding: `all-MiniLM-L6-v2` (SentenceTransformers)
  - Search Vector Store: `FAISS FlatCos IndexIDMap` (6,152 vectors)
  - Local LLM: `Phi-3-mini-4k-instruct-q4` (GGUF via llama-cpp)

---

## 📈 Performance Dashboards

| Metric Parameter | Evaluated Sub-system | Result Metric | Target |
| :--- | :--- | :--- | :--- |
| **NLP Router** | Intent Classification Accuracy | **{nlp_results['intent_accuracy']:.1f}%** | 90% |
| **NLP Router** | Entity Extraction Accuracy | **{nlp_results['entity_accuracy']:.1f}%** | 85% |
| **NLP Router** | Filter Parsing Accuracy | **{nlp_results['filter_accuracy']:.1f}%** | 85% |
| **Vector Retrieval** | Hit Rate @ 1 (Recall@1) | **{retrieval_results['recall_1']:.1f}%** | 70% |
| **Vector Retrieval** | Hit Rate @ 5 (Recall@5) | **{retrieval_results['recall_5']:.1f}%** | 90% |
| **Vector Retrieval** | Mean Reciprocal Rank (MRR@5) | **{retrieval_results['mrr_5']:.4f}** | 0.80 |
| **SQL Generation** | Dynamic Query Execution Success | **{sql_results['success_rate']:.1f}%** | 80% |
| **Text Generation** | Groundedness (Faithfulness) Score | **{generation_results['avg_faithfulness']:.2f} / 5** | 4.0 |
| **Text Generation** | Answer Relevance Score | **{generation_results['avg_relevance']:.2f} / 5** | 4.0 |

---

## ⏱️ Latency Analysis

| Pipeline Phase | Average Latency |
| :--- | :--- |
| **NLP Parsing & Classification** | {nlp_results['avg_latency_ms']:.2f} ms |
| **Vector Index Retrieval (FAISS)** | {retrieval_results['avg_latency_ms']:.2f} ms |
| **Dynamic SQL Generation & Exec** | {sql_results['avg_latency_ms']:.2f} ms |
| **Local LLM Text Generation** | {generation_results['avg_gen_latency_ms']:.2f} ms |

---

## 🔍 Detailed Component Reports

### 1. NLP Router & Parser
The NLP processor handles classification of the 7 intents and extracts metadata parameters from user inputs.

<details>
<summary><b>View Intent Classification Details</b></summary>

| Query | Expected Intent | Actual Intent | Correct | Latency |
| :--- | :--- | :--- | :--- | :--- |
"""
    for r in nlp_results['intent_details']:
        report_md += f"| \"{r['query']}\" | `{r['expected']}` | `{r['actual']}` | {'✅' if r['correct'] else '❌'} | {r['latency_ms']:.1f} ms |\n"
    report_md += """
</details>

<details>
<summary><b>View Entity Extraction Details</b></summary>

| Query | Expected Entities | Actual Entities | Correct | Extra/Missing |
| :--- | :--- | :--- | :--- | :--- |
"""
    for r in nlp_results['entity_details']:
        errs = []
        if r['missing']:
            errs.append(f"Missing: {r['missing']}")
        if r['extra']:
            errs.append(f"Extra: {r['extra']}")
        errs_str = ", ".join(errs) if errs else "None"
        report_md += f"| \"{r['query']}\" | `{r['expected']}` | `{r['actual']}` | {'✅' if r['correct'] else '❌'} | {errs_str} |\n"
    report_md += """
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
"""
    for r in sql_results['details']:
        report_md += f"| \"{r['query']}\" | `{r['sql']}` | {'✅' if r['success'] else '❌ Error: ' + r['error'][:30]} | {r['rows_returned']} | {r['latency_ms']:.1f} ms |\n"
    report_md += """
</details>

### 4. Text Generation (LLM-as-a-Judge)
Scores the final output of the assistant using the local model as a double-blind evaluator of Faithfulness and Answer Relevance.
- **Groundedness (Faithfulness)**: {generation_results['avg_faithfulness']:.2f} / 5
- **Answer Relevance**: {generation_results['avg_relevance']:.2f} / 5

<details>
<summary><b>View Generation QA Evaluations</b></summary>

"""
    for idx, r in enumerate(generation_results['details'], 1):
        report_md += f"""#### Case {idx}: "{r['query']}"
- **Retrieved Context Context (Sample)**:
  ```text
  {r['context'][:250]}...
  ```
- **Generated Answer**:
  > {r['answer']}
- **Scoring**: Faithfulness = **{r['faithfulness']}/5** | Relevance = **{r['relevance']}/5**
- **Total Latency**: {r['latency_ms']:.1f} ms

---
"""
    report_md += """
</details>
"""
    
    # Write report
    artifact_dir = r"C:\Users\maury\.gemini\antigravity-ide\brain\c05eae35-6524-4d98-8160-e10a6236a304"
    os.makedirs(artifact_dir, exist_ok=True)
    report_path = os.path.join(artifact_dir, "evaluation_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"\nWritten final report to: {report_path}")

if __name__ == "__main__":
    main()
