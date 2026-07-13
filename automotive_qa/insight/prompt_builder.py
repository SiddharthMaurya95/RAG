class PromptBuilder:
    """Constructs the optimized runtime prompt for the LLM."""
    
    def build_prompt(self, user_query: str, business_summary: str, is_raw_rows: bool = False) -> list:
        """
        Builds the prompt messages for the LLM.
        
        Args:
            user_query (str): The original query from the user.
            business_summary (str): The generated Business Summary or raw row context.
            is_raw_rows (bool): True if the summary represents raw SQL rows (when rows <= 20).
        
        Returns:
            list: List of message dictionaries (system and user prompts) suitable for the LLM.
        """
        
        system_prompt = (
            "You are a Senior Automotive Quality Assurance Manager. "
            "Generate concise business insights using ONLY the provided information.\n\n"
            "Rules:\n"
            "- Never invent facts.\n"
            "- Never estimate values.\n"
            "- Never fabricate trends.\n"
            "- Never mention SQL.\n"
            "- Never mention Python.\n"
            "- Never mention AI.\n"
            "- Never explain calculations.\n\n"
            "Output Format Constraints:\n"
            "- Return plain text ONLY. NOT JSON. NOT Markdown tables. NOT HTML.\n"
            "- Generate exactly 4 to 8 professional bullet points.\n"
            "- Each bullet must be one or two short sentences.\n"
            "- Each bullet must be maximum 35 words.\n"
            "- Mention numbers whenever available.\n"
            "- Mention percentages whenever available.\n"
            "- Mention trends only if supported.\n"
            "- Mention recommendations only if supported.\n"
            "- Every bullet must provide unique information."
        )
        
        context_type = "Raw Data Records" if is_raw_rows else "Business Summary"
        
        user_message = (
            f"User Query: {user_query}\n\n"
            f"Provided {context_type}:\n{business_summary}\n\n"
            "Based on the provided information, generate the executive insights following the constraints."
        )
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
