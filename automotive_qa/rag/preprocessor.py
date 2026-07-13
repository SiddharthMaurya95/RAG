import pandas as pd
import sqlite3
import re
import unicodedata

def load_records_to_dataframe(db_path: str) -> pd.DataFrame:
    """
    Loads all relevant records from the SQLite database into a Pandas DataFrame.
    """
    query = "SELECT * FROM records;"
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        print(f"Failed to load records from {db_path}: {e}")
        return pd.DataFrame()

def normalize_text(text: str) -> str:
    """
    Applies lightweight normalization:
    - Unicode normalization (NFKC)
    - Lowercase
    - Whitespace normalization
    - Removes obvious OCR artifacts (e.g., repeating punctuation)
    """
    if pd.isna(text) or not isinstance(text, str):
        return ""
    
    # Unicode normalization
    text = unicodedata.normalize('NFKC', text)
    
    # Lowercase
    text = text.lower()
    
    # OCR artifacts / multiple punctuation
    text = re.sub(r'[\.\,\_\-\|\:\;]{2,}', ' ', text)
    
    # Whitespace normalization
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def create_summary_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a temporary 'summary' and 'clean_summary' column by concatenating 
    Causal Parts Name, Subject, and Root Cause.
    Handles NULL values safely.
    """
    if df.empty:
        return df
        
    df = df.copy()
    
    # Handle missing columns if they don't exist in the DB schema
    for col in ['causal_parts_name', 'subject', 'root_cause']:
        if col not in df.columns:
            df[col] = ""
            
    # Safely fill NaNs with empty string for concatenation
    parts = df['causal_parts_name'].fillna("").astype(str)
    subject = df['subject'].fillna("").astype(str)
    root_cause = df['root_cause'].fillna("").astype(str)
    
    # Concatenate fields
    df['summary'] = parts + " | " + subject + " | " + root_cause
    
    # Apply normalization to create clean_summary
    df['clean_summary'] = df['summary'].apply(normalize_text)
    
    return df

def preprocess_for_embedding(db_path: str) -> pd.DataFrame:
    """
    Full preprocessing pipeline:
    1. Load records
    2. Create summary columns
    """
    df = load_records_to_dataframe(db_path)
    df = create_summary_column(df)
    return df
