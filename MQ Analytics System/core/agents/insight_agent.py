from core.ollama_client import get_client
from core.config import MODEL_NAME
import pandas as pd

client = get_client()

# def generate_insights(query, data):
#     if isinstance(data, pd.DataFrame):
#         d = data.head(20).to_string()
#     else:
#         d = str(data)

#     prompt = f"""
# Analyze data:

# Query: {query}

# Data:
# {d}

# Give:
# - Insights with numbers
# - Trends
# - anomalies
# """

#     res = client.chat(
#         model=MODEL_NAME,
#         messages=[{"role": "user", "content": prompt}]
#     )

#     return res["message"]["content"]



def generate_insights(query, data):
    if isinstance(data, pd.DataFrame):
        d = data.head(20).to_string()
    else:
        d = str(data)

    prompt = f"""
You are a data analyst.

Analyze the data based on the query.

Query:
{query}

Data:
{d}

Instructions:
- Give ONLY short insights (max 5 points)
- Each insight must be 1 line
- Include numbers where possible
- No explanation
- No introduction or conclusion
- No headings

Output format:
- Insight 1
- Insight 2
- Insight 3
"""

    res = client.chat(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    return res["message"]["content"]