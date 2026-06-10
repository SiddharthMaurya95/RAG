def select_chart_type(intent, df, query_text):
    """
    Infers the most appropriate chart type and title based on the NLP intent,
    retrieved dataframe columns, and query text.
    """
    q = query_text.lower()
    
    if df.empty:
        return "empty", "No Data Available"

    columns = [c.lower() for c in df.columns]

    # Suppress charts for simple count/total queries or single-row data unless explicitly requested
    is_chart_requested = any(w in q for w in ["chart", "graph", "plot", "visualize", "visual", "trend", "compare", "vs", "versus", "distribution", "pie", "bar", "histogram", "line", "radar"])
    is_count_query = any(w in q for w in ["total number", "how many", "count of", "number of"])
    if (df.shape[0] <= 1) or (is_count_query and not is_chart_requested):
        return "empty", "Data Summary"

    # Explicit user choice overrides
    user_requested_type = None
    if "pie" in q or "donut" in q:
        user_requested_type = "donut"
    elif "bar" in q or "histogram" in q:
        if "mileage" in columns or "using_km" in q:
            user_requested_type = "histogram"
        elif len(columns) > 2:
            user_requested_type = "grouped_bar"
        else:
            user_requested_type = "horizontal_bar"
    elif "line" in q or "trend" in q:
        user_requested_type = "line"
    elif "radar" in q or "spider" in q:
        user_requested_type = "radar"

    # Base selection defaults
    inferred_type = "horizontal_bar"
    title = "Claims Aggregations"

    # Chronological Trend Analysis
    if "period" in columns or "report_year" in columns or "trend" in q or "monthly" in q or "over time" in q:
        inferred_type = "line"
        title = "Monthly Claims Trend" if "failures" in columns else "Chronological Trend"

    # Mileage / Numeric Distribution
    elif "mileage" in columns or "using_km" in q or "distribution" in q and ("km" in q or "mileage" in q):
        inferred_type = "histogram"
        title = "Mileage (Using km) Distribution"

    # Model Comparisons
    elif intent == "COMPARE" or "compare" in q or "vs" in q or "versus" in q:
        if "resolution_rate" in columns and "avg_mileage" in columns:
            inferred_type = "radar"
            title = "Model Polar Comparison"
        else:
            inferred_type = "grouped_bar"
            title = "Grouped Claims Comparison"

    # Success / Resolution Rates
    elif "success_rate" in columns or "resolution" in q or "success" in q:
        inferred_type = "grouped_bar"
        title = "Repair Resolution Success Rate (%)"

    # Quality Distribution
    elif "quality" in columns:
        inferred_type = "donut"
        title = "Quality Rating Distribution"

    # Ranking (Dealers, Countries, Trouble Codes, Failed Parts)
    elif "failures" in columns or "count" in columns:
        if "dealer" in columns:
            inferred_type = "horizontal_bar"
            title = "Top Dealers by Failure Claims"
        elif "country" in columns:
            inferred_type = "horizontal_bar"
            title = "Top Outbreak Countries by Claims"
        elif "trouble_code" in columns:
            inferred_type = "horizontal_bar"
            title = "Most Common Failure Trouble Codes"
        elif "part_name" in columns:
            inferred_type = "horizontal_bar"
            title = "Most Common Failed Parts"
        else:
            inferred_type = "horizontal_bar"
            title = "Claims Aggregations"

    else:
        # Default fallback
        inferred_type = "grouped_bar"
        title = "Summary Data Comparison"

    # Override chart type if explicitly requested by user, but validate column limits
    final_type = user_requested_type if user_requested_type else inferred_type
    
    # Donut chart requires exactly categorical label + numeric value (2 columns)
    if final_type == "donut" and len(columns) > 2:
        final_type = inferred_type
        
    return final_type, f"{title} ({final_type.replace('_', ' ').title()})"

