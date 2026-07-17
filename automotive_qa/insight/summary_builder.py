from core.decorators import with_logging_and_exceptions

class SummaryBuilder:
    """Builds a compact textual Business Summary from the extracted metrics."""
    
    @with_logging_and_exceptions
    def build(self, metrics: dict) -> str:
        if not metrics:
            return "No data available."
            
        lines = ["# Business Summary"]
        
        ov = metrics.get("overview", {})
        if ov:
            lines.append("## 1. Dataset Overview")
            lines.append(f"- Total Records: {ov.get('total_records', 0):,}")
            lines.append(f"- Total Columns: {ov.get('total_columns', 0):,}")
            dr = ov.get("date_range")
            if dr:
                lines.append(f"- Date Range: {dr['start']} to {dr['end']}")
            lines.append(f"- Missing Values: {ov.get('missing_values', 0):,}")
            lines.append(f"- Duplicate Records: {ov.get('duplicate_records', 0):,}")
        
        tc = metrics.get("top_categories", {})
        if tc:
            lines.append("\n## 2. Top Categories")
            for col, values in tc.items():
                lines.append(f"- {col}:")
                for val in values:
                    lines.append(f"  - {val['value']} (Count: {val['count']:,}, {val['percentage']}%)")
                    
        kpis = metrics.get("kpis", [])
        if kpis:
            lines.append("\n## 3. Key Business KPIs")
            for kpi in kpis:
                lines.append(f"- {kpi['name']}: {kpi['value']} (Count: {kpi['count']:,})")
                
        trends = metrics.get("trends", {})
        if trends:
            lines.append("\n## 4. Trend Summary")
            lines.append(f"- Earliest Date: {trends.get('earliest_date')}")
            lines.append(f"- Latest Date: {trends.get('latest_date')}")
            lines.append(f"- Overall Trend: {trends.get('overall_trend')}")
            mc = trends.get("monthly_counts", {})
            if mc:
                mc_items = list(mc.items())[:12]
                mc_str = ", ".join(f"{k}: {v:,}" for k, v in mc_items)
                if len(mc) > 12:
                    mc_str += ", ..."
                lines.append(f"- Monthly Counts: {mc_str}")
            
        rels = metrics.get("relationships", [])
        if rels:
            lines.append("\n## 5. Relationships")
            for r in rels:
                lines.append(f"- {r['source_col']} ({r['source_val']}) -> {r['target_col']} ({r['target_val']}) [Count: {r['count']:,}]")
                
        # 6. Anomalies
        anoms = metrics.get("anomalies", [])
        if anoms:
            lines.append("\n## 6. Anomalies")
            for a in anoms:
                lines.append(f"- {a}")
                
        # 7. Representative Examples
        exs = metrics.get("examples", [])
        if exs:
            lines.append("\n## 7. Representative Examples")
            for i, ex in enumerate(exs, 1):
                lines.append(f"- Example {i}: {str(ex)[:250]}{'...' if len(str(ex)) > 250 else ''}")
                
        return "\n".join(lines)
