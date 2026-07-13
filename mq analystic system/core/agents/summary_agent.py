from core.ollama_client import get_client
from core.config import MODEL_NAME

client = get_client()

def summarize(insights):
    prompt = f"""
Convert into business summary:

{insights}

3 bullet points only.
"""

    res = client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    return res["message"]["content"]