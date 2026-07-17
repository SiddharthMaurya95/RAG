import pandas as pd
import numpy as np
from core.singletons import get_llm
from .engine import InsightEngine
from .summary_builder import SummaryBuilder
from .prompt_builder import PromptBuilder
import logging
from core.decorators import with_logging_and_exceptions

logger = logging.getLogger(__name__)

class InsightGenerator:
    """Orchestrates the entire insight generation pipeline."""
    
    def __init__(self):
        self.engine = InsightEngine()
        self.summary_builder = SummaryBuilder()
        self.prompt_builder = PromptBuilder()
        
    @with_logging_and_exceptions
    def generate_insight(self, query: str, df: pd.DataFrame):
        """
        Takes a dataframe and the user's query, generates a compact summary,
        and yields the LLM stream output chunk by chunk.
        """
        try:
            if df is None or df.empty:
                yield "No data available to generate insights."
                return
                
            if len(df) <= 20:
                # Prepare a clean copy of the dataframe
                df_clean = df.copy()
                
                # Convert report_month column to name of the month
                month_names = {
                    1: 'January', 2: 'February', 3: 'March', 4: 'April',
                    5: 'May', 6: 'June', 7: 'July', 8: 'August',
                    9: 'September', 10: 'October', 11: 'November', 12: 'December'
                }
                
                # Check for 'report_month' column (case-insensitive)
                for col in df_clean.columns:
                    if str(col).lower() in ('report_month', 'month'):
                        try:
                            # Map numeric months to names if they are digits/numeric
                            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').map(month_names).fillna(df_clean[col])
                        except Exception:
                            pass
                
                # Small dataset: Send directly, limit columns to top 6 to save tokens
                context = df_clean.iloc[:, :6].to_markdown(index=False)
                
                # Add pre-computed hints for the LLM to prevent calculation/reasoning errors
                hints = []
                numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    # Ignore month/year/id columns for stats
                    if any(x in str(col).lower() for x in ('year', 'month', 'id', 'code')):
                        continue
                    try:
                        max_idx = df_clean[col].idxmax()
                        min_idx = df_clean[col].idxmin()
                        
                        # Find the label for these rows (usually the first column)
                        label_col = df_clean.columns[0]
                        max_label = df_clean.loc[max_idx, label_col]
                        min_label = df_clean.loc[min_idx, label_col]
                        
                        hints.append(f"- Highest value in {col}: {df_clean.loc[max_idx, col]} (associated with {label_col}='{max_label}')")
                        hints.append(f"- Lowest value in {col}: {df_clean.loc[min_idx, col]} (associated with {label_col}='{min_label}')")
                        hints.append(f"- Total sum of {col}: {df_clean[col].sum()}")
                    except Exception:
                        pass
                
                if hints:
                    context += "\n\nPre-calculated statistics for reference:\n" + "\n".join(hints)
                    
                is_raw = True
            else:
                # Large dataset: build compact business summary
                metrics = self.engine.extract_metrics(df)
                context = self.summary_builder.build(metrics)
                is_raw = False
                
            # Hard cap context to prevent token limit errors
            if len(context) > 5000:
                context = context[:5000] + "\n... (Truncated due to length)"
                
            messages = self.prompt_builder.build_prompt(query, context, is_raw)
            
            llm_client = get_llm()
            
            # Yield chunks directly to enable UI streaming
            for chunk in llm_client.generate_chat_stream(messages):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in InsightGenerator: {e}")
            yield "Failed to generate business insights due to an internal error."
