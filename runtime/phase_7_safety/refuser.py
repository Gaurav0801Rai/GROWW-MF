import os

class SafetyRefuser:
    def __init__(self):
        self.educational_url = None

    def get_refusal(self, intent: str) -> str:
        """Returns the appropriate polite refusal message based on classified intent."""
        if intent == "ADVISORY":
            return (
                "I cannot provide investment advice, recommendations, or opinions on whether you should invest in this fund. "
                "As a facts-only assistant, I can only provide objective, verifiable information about the mutual fund schemes."
            )
        elif intent == "COMPARATIVE":
            return (
                "I cannot compare different mutual fund schemes or advise on which scheme is better. "
                "My capabilities are strictly limited to providing facts-only details for individual HDFC mutual fund schemes."
            )
        elif intent == "OUT_OF_SCOPE":
            return (
                "I cannot answer this query as it falls outside the scope of my mutual fund registry. "
                "I can only answer factual questions about the 5 allowlisted HDFC mutual fund schemes."
            )
        else:
            return (
                "I am unable to answer this question. I can only provide objective, factual details about the allowlisted HDFC mutual fund schemes."
            )
