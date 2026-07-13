def analyze_query(query):
    query = query.lower()

    if "trend" in query or "date" in query:
        return "time_series"

    if "top" in query:
        return "ranking"

    if "compare" in query:
        return "comparison"

    return "general"
