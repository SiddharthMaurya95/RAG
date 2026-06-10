import re

class NLPProcessor:
    def __init__(self):
        self.nlp = None
        # Default fallback lists
        self.countries = ["nepal", "bhutan", "india", "sri lanka", "bangladesh", "maldives", "chile", "brunei", "saudi arabia", "south africa", "indonesia", "tunisia", "uae", "united arab emirates", "uruguay", "costa rica", "philippines", "lebanon", "kuwait", "bahrain", "guatemala", "italy", "nigeria", "libya", "panama", "zimbabwe", "iraq"]
        self.db_models = set()
        self.db_countries_map = {}
        
        # Dynamically load from database if available
        try:
            import sqlite3
            from core.paths import get_db_path
            db_path = get_db_path("data/automotive.db")
            conn = sqlite3.connect(db_path)
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
                
            conn.close()
        except Exception as e:
            print(f"Error dynamically loading entities: {e}")
        
    def load_spacy(self):
        """Loads spaCy model and adds custom entity rules."""
        if self.nlp is not None:
            return
            
        try:
            import spacy
            from spacy.pipeline import EntityRuler
            # Try loading English small model
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback if model not downloaded
            print("spaCy model 'en_core_web_sm' not found, running regex-only NER.")
            return

        # Add custom EntityRuler
        ruler = self.nlp.add_pipe("entity_ruler", before="ner")
        
        # Define entity patterns
        patterns = [
            # Trouble Code (e.g. P0500, C0035)
            {"label": "TROUBLE_CODE", "pattern": [{"TEXT": {"REGEX": "^[PBCU]\\d{4}$"}}]},
            # Product Model Code (Starts with Y followed by 5 to 9 alphanumeric chars)
            {"label": "PRODUCT_MODEL", "pattern": [{"TEXT": {"REGEX": "(?i)^Y[A-Z0-9]{5,9}$"}}]},
            # Sales Model Code (e.g. ERT701, ATM412)
            {"label": "SALES_MODEL", "pattern": [{"TEXT": {"REGEX": "^[A-Z]{3}\\d{3,4}$"}}]},
            # Outbreak Country
            {"label": "COUNTRY", "pattern": [{"LOWER": {"IN": self.countries}}]},
            # FTIR No (e.g. FTIR/2024/1018)
            {"label": "FTIR_NO", "pattern": [{"TEXT": {"REGEX": "^FTIR/\\d{4}/\\d{4}$"}}]},
        ]
        ruler.add_patterns(patterns)

    def classify_intent(self, query):
        """
        Classifies intent into one of the 8 categories based on keywords.
        Returns (intent, score). If score < threshold, returns ('AMBIGUOUS', score).
        """
        q = query.lower()
        
        scores = {
            "VISUALIZE+EXPLAIN": 0,
            "VISUALIZE": 0,
            "COMPARE": 0,
            "REPORT": 0,
            "ESCALATION": 0,
            "ANALYTICS": 0,
            "SEARCH": 0
        }
        
        # 1. VISUALIZE+EXPLAIN
        if ("chart" in q or "graph" in q or "plot" in q or "visual" in q) and ("why" in q or "explain" in q or "reason" in q or "cause" in q):
            scores["VISUALIZE+EXPLAIN"] = 4
            
        # 2. VISUALIZE
        if "chart" in q or "graph" in q or "plot" in q or "visualize" in q or "show chart" in q:
            scores["VISUALIZE"] = 3
            
        # 3. COMPARE
        if "compare" in q or " vs " in q or "versus" in q or "difference between" in q:
            scores["COMPARE"] = 3
            
        # 4. REPORT
        if "monthly report" in q or "generate report" in q or "annual report" in q or "export report" in q or (("report" in q or "export" in q) and ("month" in q or "year" in q or any(yr in q for yr in ["2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029", "2030"]))):
            if "monthly report" in q or "annual report" in q:
                scores["REPORT"] = 6
            else:
                db_centric_keywords = ["unresolved", "repair", "failure", "defect", "model", "trouble", "code", "claim", "claims", "ftir", "incident", "incidents"]
                if not any(k in q for k in db_centric_keywords):
                    scores["REPORT"] = 3
            

        # 6. ANALYTICS
        if "top" in q or "count" in q or "how many" in q or "total" in q or "number" in q or "frequency" in q or "average" in q or "stats" in q or "ranking" in q or "most common" in q or "percent" in q or "rate" in q:
            scores["ANALYTICS"] = 2
            
        # 7. SEARCH
        if "similar" in q or "find" in q or "cases like" in q or "search" in q or "lookup" in q:
            scores["SEARCH"] = 3
            
        # Get highest score intent
        best_intent = max(scores, key=scores.get)
        best_score = scores[best_intent]
        
        if best_score == 0:
            return "AMBIGUOUS", 0.0
            
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
        
        # Regex definitions
        tc_pattern = re.compile(r'\b[PBCU]\d{4}\b', re.IGNORECASE)
        pm_pattern = re.compile(r'\bY[A-Z0-9]{5,9}\b', re.IGNORECASE)
        sm_pattern = re.compile(r'\b[A-Z]{3}\d{3,4}\b', re.IGNORECASE)
        vin_pattern = re.compile(r'\bMA3[A-Z0-9]{14}\b', re.IGNORECASE) # 17 chars VIN
        ftir_pattern = re.compile(r'\bFTIR/\d{4}/\d{4}\b', re.IGNORECASE)
        
        for m in tc_pattern.finditer(text):
            entities["TROUBLE_CODE"].append(m.group().upper())
            
        # Match product models via regex
        for m in pm_pattern.finditer(text):
            model_val = m.group().upper()
            if not self.db_models or model_val in self.db_models:
                entities["PRODUCT_MODEL"].append(model_val)
                
        # Also scan directly for known db_models to prevent regex omission
        if self.db_models:
            for model in self.db_models:
                if re.search(r'\b' + re.escape(model) + r'\b', text, re.IGNORECASE):
                    if model not in entities["PRODUCT_MODEL"]:
                        entities["PRODUCT_MODEL"].append(model)
                        
        for m in sm_pattern.finditer(text):
            entities["SALES_MODEL"].append(m.group().upper())
        for m in vin_pattern.finditer(text):
            entities["VIN"].append(m.group().upper())
        for m in ftir_pattern.finditer(text):
            entities["FTIR_NO"].append(m.group().upper())
            
        # Country matching
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
        
        # 1. Year filters (2020-2030)
        years = re.findall(r'\b(202\d)\b', q)
        if years:
            filters["year"] = int(years[0])
            
        # 2. Month filters
        months_map = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sep": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12
        }
        for month_name, month_num in months_map.items():
            if re.search(r'\b' + month_name + r'\b', q):
                filters["month"] = month_num
                break
                
        # 3. Limit / Top N (e.g. "top 5", "top 10")
        top_n = re.findall(r'\btop\s+(\d+)\b', q)
        if top_n:
            filters["limit"] = int(top_n[0])
        else:
            filters["limit"] = 5 # default limit
            
        # 4. Mileage filters (e.g., "under 30000 km", "less than 10k km", "before 10000 km")
        # Handle "under X km" or "less than X km" or "before X km"
        under_match = re.search(r'(?:under|less than|below|within|before)\s+([\d,]+)\s*(?:k|km)?', q)
        if under_match:
            val_str = under_match.group(1).replace(',', '')
            filters["km_max"] = int(val_str)
            
        # Handle "over X km" or "more than X km" or "after X km"
        over_match = re.search(r'(?:over|more than|above|greater than|after|exceeding)\s+([\d,]+)\s*(?:k|km)?', q)
        if over_match:
            val_str = over_match.group(1).replace(',', '')
            filters["km_min"] = int(val_str)

        # 5. Quality rating
        if "good" in q:
            filters["quality"] = "Good"
        elif "poor" in q:
            filters["quality"] = "Poor"
            
        # 6. Segmentation
        if "engine" in q:
            filters["segmentation"] = "Engine"
        elif "transmission" in q:
            filters["segmentation"] = "Transmission"
            
        return filters

    def extract_keywords(self, query):
        """Extracts significant keywords (nouns, adjectives, codes) from the query, ignoring stop words."""
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
        """
        Main entry point. Parse query and return a structured ParsedQuery object.
        """
        # Load spaCy if not loaded
        self.load_spacy()
        
        # Classify intent
        intent, intent_score = self.classify_intent(query)
        
        # Extract entities (try spaCy, fallback/combine with regex)
        entities = self.extract_entities_regex(query)
        
        if self.nlp is not None:
            doc = self.nlp(query)
            for ent in doc.ents:
                if ent.label_ in entities:
                    val = ent.text.upper() if ent.label_ != "COUNTRY" else ent.text.capitalize()
                    if val not in entities[ent.label_]:
                        entities[ent.label_].append(val)
                        
        # Extract filters
        filters = self.extract_filters(query)
        
        return {
            "query": query,
            "intent": intent,
            "intent_score": intent_score,
            "entities": entities,
            "filters": filters
        }
