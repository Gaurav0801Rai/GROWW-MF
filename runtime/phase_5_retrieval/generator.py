import os
import logging
from groq import Groq
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class Generator:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.temperature = float(os.getenv("GROQ_TEMPERATURE", "0.0"))
        
        self.client = None
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            logger.warning("GROQ_API_KEY env variable not set. Generator will fail if invoked.")

    def generate(self, query: str, context: str, citation_url: str, fetched_at: str = None) -> str:
        """Generates a facts-only response using Groq API."""
        if not self.client:
            raise ValueError("Groq client not initialized. Set GROQ_API_KEY environment variable.")
            
        system_prompt = (
            "You are a Facts-Only FAQ Assistant. Your goal is to answer the query using ONLY the context provided below.\n"
            "If the context is insufficient or does not contain the details needed to answer, state that you cannot find the details in the indexed sources.\n\n"
            "Strict Rules:\n"
            "1. Do NOT suggest or recommend any investment actions. Do NOT say things like 'this is a good investment', 'you should buy', or 'it is recommended'.\n"
            "2. Keep your response extremely concise: answer the question in exactly 1 or 2 factual sentences.\n"
            f"3. Include EXACTLY ONE markdown link citing the source URL. Format it exactly as: [Scheme Name]({citation_url}). Ensure there is no punctuation (like dots or brackets) inside the URL parenthesis.\n"
            "4. Do NOT include generic warnings or filler sentences (e.g., 'This value may change over time' or 'Please check the official page').\n"
            "5. Answer objectively without advisory bias."
        )
        
        user_prompt = f"CONTEXT:\n{context}\n\nQUERY: {query}"
        
        logger.info(f"Sending request to Groq model: {self.model_name}")
        
        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=300
        )
        
        raw_response = chat_completion.choices[0].message.content.strip()
        
        # Parse and format the last updated footer
        if fetched_at:
            try:
                # Extract YYYY-MM-DD from ISO format e.g. "2026-06-02T16:52:50" -> "2026-06-02"
                date_str = fetched_at.split("T")[0]
            except Exception:
                date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
        footer = f"\n\nLast updated from sources: {date_str}"
        
        # Ensure the response ends with the footer
        if not raw_response.endswith(date_str):
            if "Last updated from sources" not in raw_response:
                final_response = f"{raw_response}{footer}"
            else:
                final_response = raw_response
        else:
            final_response = raw_response
            
        return final_response
