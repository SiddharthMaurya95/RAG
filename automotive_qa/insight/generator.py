import pandas as pd
from core.singletons import get_llm
from .engine import InsightEngine
from .summary_builder import SummaryBuilder
from .prompt_builder import PromptBuilder
from .formatter import Formatter
import logging

logger = logging.getLogger(__name__)

class InsightGenerator:
    """Orchestrates the entire insight generation pipeline."""
    
    def __init__(self):
        self.engine = InsightEngine()
        self.summary_builder = SummaryBuilder()
        self.prompt_builder = PromptBuilder()
        self.formatter = Formatter()
        
    def generate_insight(self, query: str, df: pd.DataFrame):
        """
        Takes a dataframe and the user's query, generates a compact summary,
        and yields the LLM stream output chunk by chunk.
        """
        try:
            print(df)
            if df is None or df.empty:
                # print(df)
                yield "No data available to generate insights."
                return
                
            if len(df) <= 20:
                # Small dataset: Send directly, limit columns to top 6 to save tokens
                context = df.iloc[:, :6].to_markdown(index=False)
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
