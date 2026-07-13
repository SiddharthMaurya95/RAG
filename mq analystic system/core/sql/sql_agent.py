from core.ollama_client import get_client
from core.config import MODEL_NAME

client = get_client()

def generate_sql(query, columns):
    prompt = f"""
You are an SQL expert.

Table: data_table
Columns: {list(columns)}

Rules:
- Output ONLY SQL
- No explanation

User Query:
{query}
"""
    response = client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]