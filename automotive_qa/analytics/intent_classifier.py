import json
import sys
from typing import List, Tuple, Dict
from core.singletons import get_llm
from core.logger import get_logger
from core.custom_exception import CustomException
from core.decorators import with_logging_and_exceptions

logger = get_logger(__name__)

class Intent_classification:

    def __init__(self):
        self.nlp = None
        # basic rules (fast + reliable fallback)
        self.intent_keywords = {
            "trend": ["trend", "over time", "monthly", "yearly"],
            "comparison": ["compare", "vs", "difference", "versus"],
            "ranking": ["top", "most", "least", "highest", "lowest"],
            "distribution": ["distribution", "spread", "histogram", "range"],
            "summary": ["summary", "overall", "total", "count"],
            "anomaly": ["anomaly", "outlier", "unusual"]
        }

        self.kpi_keywords = {
            "count": ["count", "number", "how many", "amount"],
            "avg": ["average", "mean"],
            "sum": ["total", "sum"],
            "max": ["maximum", "highest"],
            "min": ["minimum", "lowest"],
            "resolution": ["resolution", "success", "solved", "fixed"]
        }

    def load_spacy(self):
        """Lazily load the spaCy model."""
        if self.nlp is not None:
            return
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            logger.warning(f"Failed to load spaCy model: {e}")
            self.nlp = None

    # =====================================================
    # RULE-BASED EXTRACTION
    # =====================================================
    @with_logging_and_exceptions
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
        aggregations = []
        
        # Heuristic rules to extract filters (extremely reliable fallback for local LLM)
        import re
        # 1. MQ Department Filter
        mq_match = re.search(r'\bmq\s*[-_]?\s*(\d+)\b', q)
        if mq_match:
            num = mq_match.group(1)
            filters.append(f"dept_of_action_judgement = 'Quality Assurance Market Quality-{num}'")
            
        # 2. Resolution Status Filter
        if "resolved" in q or "solved" in q or "closed" in q:
            filters.append("is_resolved = 1")
            
        # 3. Country Filter
        countries = ["india", "brunei", "indonesia", "vietnam", "thailand", "south africa", "nepal", "bhutan", "sri lanka"]
        for country in countries:
            if country in q:
                filters.append(f"outbreak_country = '{country.title()}'")
                
        # 4. Product Model Filter (e.g. YNC, YHB)
        model_match = re.search(r'\b(y[a-z0-9]{2,5})\b', q)
        if model_match:
            model_code = model_match.group(1).upper()
            filters.append(f"product_model_code LIKE '{model_code}%'")

        # Simple heuristic mappings (fallback if LLM misses)
        if "dealer" in q or "company" in q:
            aggregations.append("group by reported_company")
        if "country" in q:
            aggregations.append("group by outbreak_country")
        if "model" in q:
            aggregations.append("group by product_model_code")
        if "trouble code" in q or "dtc" in q:
            aggregations.append("group by trouble_code_complaint")
        if "month" in q:
            aggregations.append("group by report_month")
            
        return {
            "intents": intents,
            "kpis": kpis,
            "filters": filters,
            "aggregations": aggregations
        }

    # =====================================================
    # HYBRID SPACY + REGEX EXTRACTION
    # =====================================================
    @with_logging_and_exceptions
    def extract_hybrid(self, question: str) -> Dict:
        """Uses spaCy for robust intent/KPI extraction, and regex for rigid filters/aggregations."""
        self.load_spacy()
        
        # Base regex extraction
        base_res = self.extract_with_rules(question)
        
        if self.nlp is None:
            return base_res
            
        doc = self.nlp(question.lower())
        
        # Lemmatize and find intents/kpis based on lemmas instead of raw string matches
        lemmas = [token.lemma_ for token in doc]
        
        spacy_intents = []
        for intent, words in self.intent_keywords.items():
            for w in words:
                if len(w.split()) == 1:
                    if w in lemmas:
                        spacy_intents.append(intent)
                else:
                    if w in question.lower():
                        spacy_intents.append(intent)
                        
        spacy_kpis = []
        for kpi, words in self.kpi_keywords.items():
            for w in words:
                if len(w.split()) == 1:
                    if w in lemmas:
                        spacy_kpis.append(kpi)
                else:
                    if w in question.lower():
                        spacy_kpis.append(kpi)

        # Merge spacy results with base_res safely
        for i in spacy_intents:
            if i not in base_res["intents"]:
                base_res["intents"].append(i)
                
        for k in spacy_kpis:
            if k not in base_res["kpis"]:
                base_res["kpis"].append(k)
                
        return base_res

    # =====================================================
    # LLM EXTRACTION
    # =====================================================
    @with_logging_and_exceptions
    def extract_with_llm(self, question: str) -> Dict:
        prompt = f"""<|system|>
You are a senior data analyst mapping a user query to SQL query intents.
Extract structured intent from the query.

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
- Output only valid JSON. No explanation. No text outside JSON.
- intents: Use "trend", "comparison", "ranking", "distribution", "summary", "anomaly".
- kpis: Use "count", "avg", "sum", "max", "min", "resolution".
- filters: Translate to SQL WHERE conditions if possible (e.g., "report_year = 2024", "product_model_code LIKE 'YNC%'"). For keyword/symptom searches (like "light"), use "subject LIKE '%keyword%'". NEVER use "ftir_no" for symptoms.
- aggregations: Identify columns to GROUP BY or ORDER BY.
<|end|>
<|assistant|>
"""
        llm_client = get_llm()
        llm = llm_client.load_model()
        
        response = llm(
            prompt,
            max_tokens=256,
            temperature=0.0,
            stop=["<|end|>", "<|user|>"],
            echo=False
        )
        
        content = response["choices"][0]["text"].strip()
        
        # Find JSON block boundaries to handle any extra conversational wrapping
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx:end_idx + 1]
            
        return json.loads(content)

    # =====================================================
    # COMBINE FUNCTION
    # =====================================================
    def combine(self, a, b):
        """Merge lists safely and remove duplicates while preserving order"""
        result = []
        for item in (a + b):
            if item not in result:
                result.append(item)
        return result

    # =====================================================
    # MERGE RULE + LLM RESULTS
    # =====================================================
    def merge_results(self, rule_res, llm_res):
        def safe_get(d, key):
            if isinstance(d, dict):
                return d.get(key, [])
            return []

        return {
            "intents": self.combine(safe_get(rule_res, "intents"), safe_get(llm_res, "intents")),
            "kpis": self.combine(safe_get(rule_res, "kpis"), safe_get(llm_res, "kpis")),
            "filters": self.combine(safe_get(rule_res, "filters"), safe_get(llm_res, "filters")),
            "aggregations": self.combine(safe_get(rule_res, "aggregations"), safe_get(llm_res, "aggregations")),
        }

    # =====================================================
    # CONFIDENCE
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
    # MAIN ENTRY
    # =====================================================
    @with_logging_and_exceptions
    def build_intent_prompt(self, question: str, confidence_threshold: float = 0.8) -> Tuple[List[str], List[str], List[str], List[str]]:
        # 1. Run the ultra-fast spaCy+Regex Hybrid method
        hybrid_res = self.extract_hybrid(question)
        hybrid_confidence = self.compute_confidence(hybrid_res)

        hybrid_log = (f"--- HYBRID EXTRACTION ---\n"
                      f"Intents: {hybrid_res.get('intents')}\n"
                      f"KPIs: {hybrid_res.get('kpis')}\n"
                      f"Filters: {hybrid_res.get('filters')}\n"
                      f"Aggregations: {hybrid_res.get('aggregations')}\n"
                      f"Confidence Score: {hybrid_confidence}\n")
        
        logger.info(f"Hybrid Extraction Results:\n{hybrid_log}")

        # If hybrid confidence meets the threshold, skip LLM extraction to save time
        if hybrid_confidence >= confidence_threshold:
            logger.info(f"Hybrid confidence ({hybrid_confidence}) meets threshold ({confidence_threshold}). Skipping LLM extraction.")
            return (
                hybrid_res["intents"],
                hybrid_res["kpis"],
                hybrid_res["filters"],
                hybrid_res["aggregations"]
            )

        # 2. Run LLM Extraction to show both as requested
        logger.info(f"Hybrid confidence ({hybrid_confidence}) below threshold ({confidence_threshold}). Running LLM extraction.")
        llm_res = self.extract_with_llm(question)
        llm_confidence = self.compute_confidence(llm_res)

        llm_log = (f"--- LLM EXTRACTION ---\n"
                   f"Intents: {llm_res.get('intents')}\n"
                   f"KPIs: {llm_res.get('kpis')}\n"
                   f"Filters: {llm_res.get('filters')}\n"
                   f"Aggregations: {llm_res.get('aggregations')}\n"
                   f"Confidence Score: {llm_confidence}\n")
        
        logger.info(f"LLM Extraction Results:\n{llm_log}")
            
        final_res = self.merge_results(hybrid_res, llm_res)
        confidence = self.compute_confidence(final_res)
        logger.info(f"Intent classification complete with merged final confidence {confidence}")

        return (
            final_res["intents"],
            final_res["kpis"],
            final_res["filters"],
            final_res["aggregations"]
        )

