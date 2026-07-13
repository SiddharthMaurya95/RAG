import json
from typing import List, Tuple, Dict
from core.ollama_client import get_client
from core.config import MODEL_NAME

client = get_client()


class Intent_classification:

    def __init__(self):
        # ✅ basic rules (fast + reliable fallback)
        self.intent_keywords = {
            "trend": ["trend", "over time", "monthly", "yearly"],
            "comparison": ["compare", "vs", "difference"],
            "ranking": ["top", "most", "least", "highest"],
            "distribution": ["distribution", "spread"],
            "summary": ["summary", "overall", "total"],
            "anomaly": ["anomaly", "outlier", "unusual"]
        }

        self.kpi_keywords = {
            "count": ["count", "number", "how many"],
            "avg": ["average", "mean"],
            "sum": ["total", "sum"],
            "max": ["maximum", "highest"],
            "min": ["minimum", "lowest"]
        }

    # =====================================================
    # ✅ RULE-BASED EXTRACTION
    # =====================================================
    def extract_with_rules(self, question: str) -> Dict:
        q = question.lower()

        intents = [
            intent for intent, words in self.intent_keywords.items()
            if any(w in q for w in words)
        ]

        kpis = [
            kpi for kpi, words in self.kpi_keywords.items()
            if any(w in q for w in words)
        ]

        filters = []
        if "japan" in q:
            filters.append("country = Japan")
        if "india" in q:
            filters.append("country = India")

        if "last year" in q:
            filters.append("year = last year")
        if "last month" in q:
            filters.append("month = last month")

        aggregations = []
        if "month" in q:
            aggregations.append("group by month")
        if "country" in q:
            aggregations.append("group by country")

        return {
            "intents": intents,
            "kpis": kpis,
            "filters": filters,
            "aggregations": aggregations
        }

    # =====================================================
    # ✅ LLM EXTRACTION
    # =====================================================
    def extract_with_llm(self, base_instructions: str, question: str) -> Dict:

        prompt = f"""
You are a senior data analyst.

Extract structured intent from the query.

----------------------------------------
CONTEXT
----------------------------------------
{base_instructions}

----------------------------------------
USER QUERY
----------------------------------------
{question}

----------------------------------------
OUTPUT STRICT JSON ONLY
----------------------------------------
{{
  "intents": [],
  "kpis": [],
  "filters": [],
  "aggregations": []
}}

Rules:
- No explanation
- No text outside JSON
"""

        response = client.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response["message"]["content"]

        try:
            return json.loads(content)
        except Exception:
            return {"intents": [], "kpis": [], "filters": [], "aggregations": []}

    # =====================================================
    # ✅ COMBINE FUNCTION (FIXED)
    # =====================================================
    def combine(self, a, b):
        """Merge lists safely and remove duplicates while preserving order"""
        result = []
        for item in (a + b):
            if item not in result:
                result.append(item)
        return result

    # =====================================================
    # ✅ MERGE RULE + LLM RESULTS (FIXED)
    # =====================================================
    def merge_results(self, rule_res, llm_res):
        def safe_get(d, key):
            if isinstance(d, dict):
                return d.get(key, [])
            return []

        return {
            "intents": self.combine(
                safe_get(rule_res, "intents"),
                safe_get(llm_res, "intents")
            ),
            "kpis": self.combine(
                safe_get(rule_res, "kpis"),
                safe_get(llm_res, "kpis")
            ),
            "filters": self.combine(
                safe_get(rule_res, "filters"),
                safe_get(llm_res, "filters")
            ),
            "aggregations": self.combine(
                safe_get(rule_res, "aggregations"),
                safe_get(llm_res, "aggregations")
            ),
        }

    # =====================================================
    # ✅ CONFIDENCE
    # =====================================================
    def compute_confidence(self, result: Dict) -> float:
        score = 0
        if result["intents"]:
            score += 0.3
        if result["kpis"]:
            score += 0.3
        if result["filters"]:
            score += 0.2
        if result["aggregations"]:
            score += 0.2
        return round(score, 2)

    # =====================================================
    # ✅ MAIN ENTRY
    # =====================================================
    def build_intent_prompt(
        self,
        base_instructions: str,
        question: str
    ) -> Tuple[List[str], List[str], List[str], List[str]]:

        rule_res = self.extract_with_rules(question)
        llm_res = self.extract_with_llm(base_instructions, question)

        final_res = self.merge_results(rule_res, llm_res)
        confidence = self.compute_confidence(final_res)

        print("✅ Intent Extraction Result:", final_res)
        print("✅ Confidence Score:", confidence)

        return (
            final_res["intents"],
            final_res["kpis"],
            final_res["filters"],
            final_res["aggregations"]
        )