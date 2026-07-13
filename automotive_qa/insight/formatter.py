import re

class Formatter:
    """Cleans and validates the LLM output before sending it to the frontend."""
    
    def clean_output(self, raw_output: str) -> str:
        """
        Cleans the LLM output.
        Removes JSON formatting, markdown tables, HTML, etc., if any.
        Ensures output is bulleted plain text.
        """
        # Remove any markdown code blocks
        clean_text = re.sub(r'```.*?```', '', raw_output, flags=re.DOTALL)
        
        # Split into lines
        lines = clean_text.strip().split('\n')
        
        bullets = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Remove HTML tags
            line = re.sub(r'<[^>]+>', '', line)
            
            # Format as bullet
            if line.startswith(('- ', '* ', '• ')):
                bullets.append(line)
            elif re.match(r'^\d+\.\s+', line):
                # convert numbered lists to bullet
                line = re.sub(r'^\d+\.\s+', '- ', line)
                bullets.append(line)
            else:
                # Force bullet
                bullets.append(f"- {line}")
                
        # Limit to 4-8 bullets (just to enforce strict rules if LLM failed)
        if len(bullets) > 8:
            bullets = bullets[:8]
            
        return "\n\n".join(bullets)
