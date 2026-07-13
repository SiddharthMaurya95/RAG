# =====================================================
# ✅ NLP PROCESSOR MODULE
# =====================================================
import re

class NLPProcessor:
    def __init__(self):
        self.nlp = None
        self.countries = []
        self.db_countries_map = {}
        self.db_models = set()
        self.db_sales_models = set()
        self.db_tcs = set()
        
        # Dynamically load from database if available
        try:
            from core.database import get_engine
            from core.paths import get_db_path
            db_path = get_db_path("data/automotive.db")
            conn = get_engine(db_path).raw_connection()
            cursor = conn.cursor()
            
            # Load countries and build mapping for case preservation
            cursor.execute("SELECT DISTINCT outbreak_country FROM records WHERE outbreak_country IS NOT NULL;")
            db_countries = [row[0].strip() for row in cursor.fetchall() if row[0]]
            if db_countries:
                self.countries = list(set([c.lower() for c in db_countries]))
                self.db_countries_map = {c.lower(): c for c in db_countries}
                
                # Add common synonyms/expansions
                syns = {
                    "uae": "UNITED ARAB EMIRATES",
                    "united arab emirates": "UAE",
                    "usa": "USA",
                    "us": "US",
                    "united states": "USA"
                }
                for k, v in syns.items():
                    if k not in self.db_countries_map:
                        self.db_countries_map[k] = v
                    if k not in self.countries:
                        self.countries.append(k)
                        
            # Load product model codes
            cursor.execute("SELECT DISTINCT product_model_code FROM records WHERE product_model_code IS NOT NULL;")
            db_models = [row[0].strip().upper() for row in cursor.fetchall() if row[0]]
            if db_models:
                self.db_models = set(db_models)
                
            cursor.execute("SELECT DISTINCT sales_model_code FROM records WHERE sales_model_code IS NOT NULL;")
            db_sales_models = [row[0].strip().upper() for row in cursor.fetchall() if row[0]]
            if db_sales_models:
                self.db_sales_models = set(db_sales_models)
                
            cursor.execute("SELECT DISTINCT trouble_code_complaint FROM records WHERE trouble_code_complaint IS NOT NULL;")
            db_tcs = [row[0].strip().upper() for row in cursor.fetchall() if row[0]]
            if db_tcs:
                self.db_tcs = set(db_tcs)
                
            conn.close()
        except Exception as e:
            print(f"Error dynamically loading entities: {e}")
        
    def load_spacy(self):
        """Loads spaCy model and adds custom entity rules."""
        if self.nlp is not None:
            return
            
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
        except Exception as e:
            print(f"spaCy could not be loaded ({e}), running regex-only NER.")
            return

        # Add custom EntityRuler
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        
        # Define entity patterns
        patterns = [
            {"label": "TROUBLE_CODE", "pattern": [{"TEXT": {"REGEX": "(?i)^[PBCU]\\d{1,4}$"}}]},
            {"label": "PRODUCT_MODEL", "pattern": [{"TEXT": {"REGEX": "(?i)^Y[A-Z0-9]{2,9}$"}}]},
            {"label": "SALES_MODEL", "pattern": [{"TEXT": {"REGEX": "(?i)^[A-Z]{3}\\d{0,4}$"}}]},
            {"label": "COUNTRY", "pattern": [{"LOWER": {"IN": self.countries}}]},
            {"label": "FTIR_NO", "pattern": [{"TEXT": {"REGEX": "^FTIR/\\d{4}/\\d{4}$"}}]},
        ]
        ruler.add_patterns(patterns)

    def classify_intent(self, query):
        """Classifies intent into one of the 4 categories based on keywords."""
        q = query.lower()
        
        scores = {
            "VISUALIZE+EXPLAIN": 0,
            "REPORT": 0,
            "ANALYTICS": 0,
            "SEARCH": 0
        }
        
        def has_word(kw):
            return bool(re.search(r'\b' + re.escape(kw) + r'\b', q))

        if has_word("chart") or has_word("graph") or has_word("plot") or has_word("visualize") or "show chart" in q or has_word("visual"):
            scores["VISUALIZE+EXPLAIN"] = 4
            
        if has_word("compare") or has_word("versus") or "difference between" in q or (" vs " in q and not (has_word("total") or has_word("count") or "how many" in q)):
            scores["VISUALIZE+EXPLAIN"] = max(scores["VISUALIZE+EXPLAIN"], 3)
            
        has_report_action = any(has_word(act) for act in ["generate", "create", "export"]) and has_word("report")
        if "monthly report" in q or "annual report" in q or has_report_action or has_word("pdf") or "report pdf" in q or "summary pdf" in q:
            scores["REPORT"] = 5
        elif has_word("report") and (has_word("month") or has_word("year") or any(has_word(yr) for yr in ["2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"])):
            db_centric_keywords = ["unresolved", "repair", "failure", "defect", "model", "trouble", "code", "claim", "claims", "ftir", "incident", "incidents"]
            if not any(has_word(k) for k in db_centric_keywords):
                scores["REPORT"] = 3
            
        analytics_keywords = ["top", "count", "how many", "total", "number", "frequency", "average", "stats", "ranking", "most common", "percent", "rate"]
        if any(has_word(k) for k in analytics_keywords):
            scores["ANALYTICS"] = 2.5
            
        search_keywords = ["similar", "find", "cases like", "search", "lookup", "glowing", "stalling", "rattling", "noise", "peeling", "jerky", "misfire", "corrosion", "shift", "solenoid", "dtc", "mil", "p0", "p1", "p2", "p3", "c1", "u0", "bumper", "rough", "light", "stalls", "stalled", "rust"]
        if any(has_word(k) for k in search_keywords):
            scores["SEARCH"] = 1
        if has_word("similar") or has_word("find") or "cases like" in q or has_word("search") or has_word("lookup"):
            scores["SEARCH"] = 3
            
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        if best_score == 0:
            return "SEARCH", 0.0
            
        return best_intent, float(best_score)

    def extract_entities_regex(self, text):
        """Backup regex entity extraction."""
        entities = {
            "TROUBLE_CODE": [],
            "PRODUCT_MODEL": [],
            "SALES_MODEL": [],
            "COUNTRY": [],
            "VIN": [],
            "FTIR_NO": []
        }
        
        tc_pattern = re.compile(r'\b[PBCU]\d{1,4}\b', re.IGNORECASE)
        pm_pattern = re.compile(r'\bY[A-Z0-9]{2,9}\b', re.IGNORECASE)
        sm_pattern = re.compile(r'\b[A-Z]{3}\d{0,4}\b', re.IGNORECASE)
        vin_pattern = re.compile(r'\bMA3[A-Z0-9]{14}\b', re.IGNORECASE)
        ftir_pattern = re.compile(r'\bFTIR/\d{4}/\d{4}\b', re.IGNORECASE)
        
        for m in tc_pattern.finditer(text):
            code_val = m.group().upper()
            if not self.db_tcs or code_val in self.db_tcs or (len(code_val) < 5 and any(m.startswith(code_val) for m in self.db_tcs)):
                entities["TROUBLE_CODE"].append(code_val)
            
        for m in pm_pattern.finditer(text):
            model_val = m.group().upper()
            if not self.db_models or model_val in self.db_models or (len(model_val) < 5 and any(m.startswith(model_val) for m in self.db_models)):
                entities["PRODUCT_MODEL"].append(model_val)
                
        if self.db_models:
            for model in self.db_models:
                if re.search(r'\b' + re.escape(model) + r'\b', text, re.IGNORECASE):
                    if model not in entities["PRODUCT_MODEL"]:
                        entities["PRODUCT_MODEL"].append(model)
                        
        for m in sm_pattern.finditer(text):
            model_val = m.group().upper()
            if not self.db_sales_models or model_val in self.db_sales_models or (len(model_val) < 6 and any(m.startswith(model_val) for m in self.db_sales_models)):
                entities["SALES_MODEL"].append(model_val)
        for m in vin_pattern.finditer(text):
            entities["VIN"].append(m.group().upper())
        for m in ftir_pattern.finditer(text):
            entities["FTIR_NO"].append(m.group().upper())
            
        for country in self.countries:
            if re.search(r'\b' + re.escape(country) + r'\b', text, re.IGNORECASE):
                db_casing = self.db_countries_map.get(country.lower(), country.title())
                if db_casing not in entities["COUNTRY"]:
                    entities["COUNTRY"].append(db_casing)
                    
        return entities

    def extract_filters(self, text):
        """Extracts SQL query filters like years, months, mileage limits, and quality ratings."""
        filters = {}
        q = text.lower()
        
        years = re.findall(r'\b(202\d)\b', q)
        if years:
            filters["year"] = int(years[0])
            
        months_map = {
            "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
            "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
            "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
            "november": 11, "nov": 11, "december": 12, "dec": 12
        }
        for month_name, month_num in months_map.items():
            if re.search(r'\b' + month_name + r'\b', q):
                filters["month"] = month_num
                break
                
        top_n = re.findall(r'\btop\s+(\d+)\b', q)
        if top_n:
            filters["limit"] = int(top_n[0])
        else:
            filters["limit"] = 5
            
        under_match = re.search(r'(?:under|less than|below|within|before)\s+([\d,]+)\s*(?:k|km)?', q)
        if under_match:
            val_str = under_match.group(1).replace(',', '')
            filters["km_max"] = int(val_str)
            
        over_match = re.search(r'(?:over|more than|above|greater than|after|exceeding)\s+([\d,]+)\s*(?:k|km)?', q)
        if over_match:
            val_str = over_match.group(1).replace(',', '')
            filters["km_min"] = int(val_str)

        if "good" in q:
            filters["quality"] = "Good"
        elif "poor" in q:
            filters["quality"] = "Poor"
            
        if "engine" in q:
            filters["segmentation"] = "Engine"
        elif "transmission" in q:
            filters["segmentation"] = "Transmission"
            
        return filters

    def extract_keywords(self, query):
        """Extracts significant keywords from the query, ignoring stop words."""
        self.load_spacy()
        
        stop_words = {"give", "me", "total", "number", "of", "ftir", "with", "problems", "related", "to", "show", "find", "search", "list", "all", "any", "the", "a", "an", "in", "on", "at", "for", "about", "cases", "reports", "incident", "incidents", "failure", "failures", "issue", "issues", "problem", "defect", "defects", "how", "many", "what", "where", "who", "tell", "explain", "get", "whose", "is", "was", "were", "are", "has", "have", "had", "company", "report", "country", "by", "from", "it", "its", "that", "this", "these", "those", "than", "or", "and"}
        
        keywords = []
        if self.nlp is not None:
            doc = self.nlp(query)
            for token in doc:
                if token.pos_ in ("NOUN", "PROPN", "ADJ") and token.text.lower() not in stop_words:
                    keywords.append(token.text.lower())
        else:
            words = re.findall(r'\b\w+\b', query.lower())
            for w in words:
                if w not in stop_words and len(w) > 2:
                    keywords.append(w)
        return keywords

    def parse_query(self, query):
        """Main entry point. Parse query and return a structured dict."""
        self.load_spacy()
        intent, intent_score = self.classify_intent(query)
        entities = self.extract_entities_regex(query)
        
        if self.nlp is not None:
            doc = self.nlp(query)
            for ent in doc.ents:
                if ent.label_ in entities:
                    val = ent.text.upper() if ent.label_ != "COUNTRY" else ent.text.capitalize()
                    if val not in entities[ent.label_]:
                        entities[ent.label_].append(val)
                        
        filters = self.extract_filters(query)
        
        return {
            "query": query,
            "intent": intent,
            "intent_score": intent_score,
            "entities": entities,
            "filters": filters
        }
