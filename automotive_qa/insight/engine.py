import pandas as pd
import numpy as np
import logging

from core.decorators import with_logging_and_exceptions

logger = logging.getLogger(__name__)

class InsightEngine:
    """Extracts useful analytics from Pandas DataFrame for Business Summary generation."""
    
    @with_logging_and_exceptions
    def extract_metrics(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {}
            
        metrics = {
            "overview": self._get_overview(df),
            "top_categories": self._get_top_categories(df),
            "kpis": self._get_kpis(df),
            "trends": self._get_trends(df),
            "relationships": self._get_relationships(df),
            "anomalies": self._get_anomalies(df),
            "examples": self._get_examples(df)
        }
        return metrics

    def _get_overview(self, df: pd.DataFrame) -> dict:
        total_records = len(df)
        total_columns = len(df.columns)
        missing_values = df.isna().sum().sum()
        duplicate_records = df.duplicated().sum()
        
        date_cols = df.select_dtypes(include=['datetime64']).columns
        date_range = None
        if not date_cols.empty:
            first_date_col = date_cols[0]
            date_range = {
                "start": str(df[first_date_col].min()),
                "end": str(df[first_date_col].max())
            }
        elif 'report_year' in df.columns and 'report_month' in df.columns:
            try:
                df_dates = df.dropna(subset=['report_year', 'report_month']).copy()
                df_dates['report_year'] = pd.to_numeric(df_dates['report_year'], errors='coerce')
                df_dates['report_month'] = pd.to_numeric(df_dates['report_month'], errors='coerce')
                df_dates = df_dates.dropna(subset=['report_year', 'report_month'])
                
                if not df_dates.empty:
                    min_row = df_dates.sort_values(['report_year', 'report_month']).iloc[0]
                    max_row = df_dates.sort_values(['report_year', 'report_month']).iloc[-1]
                    date_range = {
                        "start": f"{int(min_row['report_year'])}-{int(min_row['report_month']):02d}",
                        "end": f"{int(max_row['report_year'])}-{int(max_row['report_month']):02d}"
                    }
            except Exception as e:
                logger.warning(f"Failed to parse date range from year/month columns: {e}")
            
        return {
            "total_records": total_records,
            "total_columns": total_columns,
            "missing_values": int(missing_values),
            "duplicate_records": int(duplicate_records),
            "date_range": date_range
        }
        
    def _get_top_categories(self, df: pd.DataFrame) -> dict:
        # Detect useful categorical columns
        cat_cols = df.select_dtypes(include=['object', 'string', 'category']).columns
        top_cats = {}
        for col in cat_cols:
            n_unique = df[col].nunique()
            if 1 < n_unique < len(df) and n_unique < 100:  # Only summarize meaningful categories
                counts = df[col].value_counts().head(5)
                percentages = df[col].value_counts(normalize=True).head(5) * 100
                top_cats[col] = [
                    {"value": str(val), "count": int(count), "percentage": round(float(pct), 2)}
                    for val, count, pct in zip(counts.index, counts.values, percentages.values)
                ]
        return top_cats

    def _get_kpis(self, df: pd.DataFrame) -> list:
        # Automatically determine Most Affected Entity
        kpis = []
        kpi_mapping = {
            "Most Affected Model": ["product_model_code", "sales_model_code", "model", "sales_model", "vehicle_model"],
            "Most Common Root Cause": ["causal_parts_name", "root_cause", "trouble_code_defect", "causal_part"],
            "Most Common Complaint": ["customer_complaint", "complaint"],
            "Most Affected Supplier": ["reported_company", "supplier", "company"],
            "Most Affected Country": ["outbreak_country", "country", "nation"],
            "Most Affected Plant": ["issued_company", "plant", "factory"],
            "Most Frequent Failure": ["trouble_code_complaint", "trouble_code_defect", "failure", "dtc"]
        }
        
        used_cols = set()
        for kpi_name, possible_cols in kpi_mapping.items():
            if len(kpis) >= 10:
                break
            for col in df.columns:
                if col.lower() in possible_cols and col not in used_cols:
                    if not df[col].empty and df[col].notna().any():
                        counts = df[col].value_counts()
                        if not counts.empty:
                            top_val = counts.idxmax()
                            count = counts.max()
                            kpis.append({"name": kpi_name, "value": str(top_val), "count": int(count), "column": col})
                            used_cols.add(col)
                            break
        return kpis

    def _get_trends(self, df: pd.DataFrame) -> dict:
        date_cols = df.select_dtypes(include=['datetime64']).columns
        monthly = pd.Series(dtype=int)
        
        if not date_cols.empty:
            date_col = date_cols[0]
            s = df[date_col].dropna()
            if not s.empty:
                monthly = s.groupby(s.dt.to_period('M')).size()
        elif "report_year" in df.columns and "report_month" in df.columns:
            df_valid = df.dropna(subset=['report_year', 'report_month']).copy()
            df_valid['report_year'] = pd.to_numeric(df_valid['report_year'], errors='coerce')
            df_valid['report_month'] = pd.to_numeric(df_valid['report_month'], errors='coerce')
            df_valid = df_valid.dropna(subset=['report_year', 'report_month'])
            if not df_valid.empty:
                try:
                    df_valid['period'] = df_valid['report_year'].astype(int).astype(str) + "-" + df_valid['report_month'].astype(int).astype(str).str.zfill(2)
                    monthly = df_valid.groupby('period').size().sort_index()
                except Exception as e:
                    logger.warning(f"Failed to calculate monthly trends: {e}")
                    
        if len(monthly) < 2:
            return {}
            
        first_val, last_val = monthly.iloc[0], monthly.iloc[-1]
        overall_trend = "Stable"
        if last_val > first_val * 1.1:
            overall_trend = "Increasing"
        elif last_val < first_val * 0.9:
            overall_trend = "Decreasing"
            
        # Select evenly distributed samples if there are too many months
        monthly_dict = {str(k): int(v) for k, v in monthly.items()}
        if len(monthly_dict) > 12:
            keys = list(monthly_dict.keys())
            indices = np.linspace(0, len(keys)-1, 12, dtype=int)
            monthly_dict = {keys[i]: monthly_dict[keys[i]] for i in indices}
            
        return {
            "earliest_date": str(monthly.index[0]),
            "latest_date": str(monthly.index[-1]),
            "monthly_counts": monthly_dict,
            "overall_trend": overall_trend
        }

    def _get_relationships(self, df: pd.DataFrame) -> list:
        rels = []
        cat_cols = df.select_dtypes(include=['object', 'string', 'category']).columns
        if len(cat_cols) < 2:
            return rels
            
        # Common source/target definitions
        source_cols = [c for c in cat_cols if any(x in c.lower() for x in ["model", "country", "supplier", "plant", "company"])]
        target_cols = [c for c in cat_cols if any(x in c.lower() for x in ["root_cause", "complaint", "defect", "causal", "trouble"])]
        
        for sc in source_cols:
            for tc in target_cols:
                if sc == tc: continue
                if len(rels) >= 5: break
                
                crosstab = pd.crosstab(df[sc], df[tc])
                if crosstab.empty: continue
                
                max_val = crosstab.values.max()
                if max_val > 0:
                    max_idx = np.unravel_index(crosstab.values.argmax(), crosstab.values.shape)
                    source_val = crosstab.index[max_idx[0]]
                    target_val = crosstab.columns[max_idx[1]]
                    rels.append({
                        "source_col": sc, "target_col": tc,
                        "source_val": str(source_val), "target_val": str(target_val),
                        "count": int(max_val)
                    })
        return rels

    def _get_anomalies(self, df: pd.DataFrame) -> list:
        anomalies = []
        if df.isna().sum().sum() > (len(df) * len(df.columns) * 0.2):
            anomalies.append("High missing data: Over 20% of the dataset values are missing.")
            
        cat_cols = df.select_dtypes(include=['object', 'string', 'category']).columns
        for col in cat_cols:
            if len(anomalies) >= 5: break
            counts = df[col].value_counts()
            if len(counts) > 2:
                mean = counts.mean()
                std = counts.std()
                if std > 0:
                    max_count = counts.iloc[0]
                    if (max_count - mean) / std > 3:
                        anomalies.append(f"Spike detected in {col}: '{counts.index[0]}' has exceptionally high occurrences ({max_count}).")
                        
        return anomalies

    def _get_examples(self, df: pd.DataFrame) -> list:
        examples = []
        possible_cols = []
        for target in ["complaint", "subject", "root_cause", "trouble_code", "repair", "causal_parts"]:
            for col in df.columns:
                if target in col.lower() and col not in possible_cols:
                    possible_cols.append(col)
                    
        if not possible_cols:
            return examples
            
        sample_df = df[possible_cols].dropna(how='all').head(5)
        for _, row in sample_df.iterrows():
            examples.append({col: str(val) for col, val in row.items() if pd.notna(val) and val != "" and str(val).lower() != "nan"})
            
        return examples
