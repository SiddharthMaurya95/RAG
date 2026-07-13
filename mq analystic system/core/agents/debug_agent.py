from core.ollama_client import get_client
from core.config import MODEL_NAME

client = get_client()

def fix_code(code, error):
    prompt = f"""
Fix Python code.

Code:
{code}

Error:
{error}

Return only corrected code.
"""

    response = client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    return response["message"]["content"]
