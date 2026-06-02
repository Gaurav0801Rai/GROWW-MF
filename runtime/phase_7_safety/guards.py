import re
import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ResponseGuard:
    def __init__(self, registry_path="ingest/registry.json"):
        self.registry_path = registry_path
        self.allowed_urls = set()
        
        # Load allowed URLs from registry
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                    for scheme in registry.get("schemes", []):
                        self.allowed_urls.add(scheme["url"])
            except Exception as e:
                logger.error(f"Failed to load allowed URLs in ResponseGuard: {e}")
                
        # Default allowlist fallback in case file load fails
        if not self.allowed_urls:
            self.allowed_urls = {
                "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
                "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
                "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
                "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
                "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth"
            }
            
        # Prohibited advisory words/phrases
        self.prohibited_keywords = [
            r"\brecommend\b", r"\brecommends\b", r"\brecommendation\b",
            r"\byou\s+should\b", r"\bshould\s+you\b", r"\bwe\s+suggest\b",
            r"\bbetter\s+returns?\b", r"\bbest\s+option\b", r"\bhighly\s+suggested\b",
            r"\bsafe\s+bet\b", r"\binvestment\s+advice\b", r"\bgood\s+choice\b",
            r"\bgood\s+investment\b", r"\bbest\s+investment\b"
        ]

    def validate(self, text: str) -> tuple[bool, str]:
        """Runs programmatic checks. Returns (is_valid, reason)."""
        # 1. Advisory Keywords Check
        for kw in self.prohibited_keywords:
            if re.search(kw, text.lower()):
                return False, f"Advisory keyword violation (matched: '{kw}')"
                
        # Split text into body and footer (isolated by Last updated from sources)
        body_text = text
        if "Last updated from sources" in text:
            body_text = text.split("Last updated from sources")[0].strip()
            
        # 2. Sentence Count Check
        # Split body text by sentence boundaries (periods, exclamations, questions)
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', body_text) if s.strip()]
        if len(sentences) > 3:
            return False, f"Sentence count violation (contains {len(sentences)} sentences, max allowed is 3)"
            
        # 3. Markdown Link Check
        # Extract markdown links of format [anchor](url)
        links = re.findall(r'\[([^\]]*)\]\((https?://[^\)]+)\)', text)
        if len(links) != 1:
            # Check if there is an unanchored URL instead
            unanchored_urls = re.findall(r'(https?://[^\s\)]+)', text)
            if len(unanchored_urls) == 1:
                url = unanchored_urls[0]
            else:
                return False, f"Link count violation (contains {len(links)} markdown links and {len(unanchored_urls)} raw URLs, exactly 1 link required)"
        else:
            url = links[0][1]
            
        # Clean URL trailing characters if any
        url = url.strip()
        
        # 4. Allowlisted URL Check
        if url not in self.allowed_urls:
            # We also allow the default AMFI educational corner url for refusals
            educational_url = "https://www.amfiindia.com/investor-corner/investor-education"
            if url != educational_url:
                return False, f"URL violation (url '{url}' is not in the allowlist)"
                
        return True, "Valid"

    def execute_with_correction(self, generator, query: str, context: str, citation_url: str, fetched_at: str = None) -> str:
        """Executes LLM generation, runs validation, performs 1 retry correction, or falls back."""
        # First attempt
        response = generator.generate(query, context, citation_url, fetched_at)
        is_valid, reason = self.validate(response)
        
        if is_valid:
            logger.info("First attempt generation passed safety guardrails.")
            return response
            
        logger.warning(f"First attempt generation failed guardrails: {reason}. Triggering self-correction retry...")
        
        corrective_context = (
            f"{context}\n\n"
            "CORRECTION INSTRUCTION (CRITICAL):\n"
            "Your previous answer failed validation due to: " + reason + ".\n"
            "You MUST strictly follow these rules:\n"
            "1. Answer the query in exactly 1 or 2 factual sentences. Do NOT exceed 2 sentences.\n"
            f"2. Include EXACTLY ONE markdown link pointing to: {citation_url}. Format it exactly as: [Scheme Name]({citation_url}). Do NOT put punctuation (like periods or brackets) inside the URL parenthesis.\n"
            "3. Do NOT include generic warnings, filler sentences, or disclaimer text.\n"
            "4. Do NOT provide investment advice or recommendations. Use objective language."
        )
        
        # Second attempt
        try:
            retry_response = generator.generate(query, corrective_context, citation_url, fetched_at)
            is_valid_retry, reason_retry = self.validate(retry_response)
            
            if is_valid_retry:
                logger.info("Second attempt (self-correction) generation passed safety guardrails.")
                return retry_response
                
            logger.error(f"Second attempt failed guardrails: {reason_retry}. Proceeding to fallback...")
        except Exception as e:
            logger.error(f"Error during self-correction generation: {e}. Proceeding to fallback...")
            
        # Fallback to static compliant response
        date_str = fetched_at.split("T")[0] if fetched_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Find scheme name from allowed URLs mapping
        scheme_name = "HDFC Mutual Fund Scheme"
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r", encoding="utf-8") as f:
                    registry = json.load(f)
                    for scheme in registry.get("schemes", []):
                        if scheme["url"] == citation_url:
                            scheme_name = scheme["name"]
                            break
            except Exception:
                pass
                
        fallback_response = (
            f"Here is the official information regarding the {scheme_name}. "
            f"Please refer directly to the canonical scheme page on Groww to check all factual parameters: [{scheme_name}]({citation_url}).\n\n"
            f"Last updated from sources: {date_str}"
        )
        
        return fallback_response
