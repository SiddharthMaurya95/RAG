import os

app_path = "MQ Analytics System/app.py"

with open(app_path, "r", encoding="utf-8") as f:
    text = f.read()

# Perform replacements for imports
text = text.replace("from auth.session import", "from core.memory.session import")
text = text.replace("from core.router import QueryRouter", "from core.pipeline import QueryRouter")
text = text.replace("from viz.charts import", "from core.utils.charts import")
text = text.replace("from reports.engine import", "from core.utils.report_engine import")
text = text.replace("from analytics.engine import", "from core.sql.sql_executor import")

# Fix reload list
text = text.replace(
    '["auth.session", "core.singletons", "core.router", "core.paths", "viz.charts", "reports.engine", "analytics.engine", "analytics.graph_selector", "nlp.pipeline", "llm.client"]',
    '["core.memory.session", "core.singletons", "core.pipeline", "core.paths", "core.utils.charts", "core.utils.report_engine", "core.sql.sql_executor", "core.ollama_client"]'
)

# Replace the Page title to keep the MQ branding
text = text.replace('page_title="Automotive QA Intelligence"', 'page_title="MQ Quality & Analytics Intelligence"')

with open(app_path, "w", encoding="utf-8") as f:
    f.write(text)

print("Replacements completed successfully.")
