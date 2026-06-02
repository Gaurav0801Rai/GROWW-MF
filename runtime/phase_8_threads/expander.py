import logging

logger = logging.getLogger(__name__)

class QueryExpander:
    def __init__(self, generator):
        self.generator = generator

    def expand(self, query: str, history: list[dict]) -> str:
        """Contextualizes follow-up queries using the last 4-6 thread messages."""
        if not history:
            return query
            
        # Format conversation history context for the LLM
        history_str = ""
        # Cap at the last 6 messages
        for msg in history[-6:]:
            role_label = "Investor" if msg["role"] == "user" else "Assistant"
            history_str += f"{role_label}: {msg['content']}\n"
            
        system_prompt = (
            "You are an expert query expansion engine. Your task is to rewrite the latest user message to be a single, self-contained search query, using the conversation history for context.\n"
            "If the latest message is a follow-up referring to previous funds, nouns, or pronouns (like 'it', 'he', 'they', 'its NAV', 'that fund'), replace them with the specific mutual fund scheme names or entities mentioned in the history.\n"
            "If the latest message is already self-contained and does not require context from history, output the latest message EXACTLY as it is, without any modifications.\n"
            "Do NOT add any conversational headers, explanations, or quotes. Output ONLY the rewritten query."
        )
        
        user_prompt = f"CONVERSATION HISTORY:\n{history_str}\nLATEST USER MESSAGE: {query}\n\nREWRITTEN QUERY:"
        
        try:
            logger.info("Triggering query expansion for user message...")
            chat_completion = self.generator.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.generator.model_name,
                temperature=0.0,
                max_tokens=100
            )
            expanded_query = chat_completion.choices[0].message.content.strip()
            
            # Clean enclosing quotes if LLM added them
            if expanded_query.startswith('"') and expanded_query.endswith('"'):
                expanded_query = expanded_query[1:-1].strip()
                
            logger.info(f"Query expanded successfully: '{query}' -> '{expanded_query}'")
            return expanded_query
        except Exception as e:
            # On API failures, log error and fall back to original query to maintain resilience
            logger.error(f"Query expansion failed: {e}. Falling back to original query.")
            return query
