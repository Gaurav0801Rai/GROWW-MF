import re

class IntentRouter:
    def __init__(self):
        # Comparative regex patterns
        self.comparative_patterns = [
            r"\bwhich\s+(?:is|was|would\s+be)\s+(?:better|best|greater|higher|more|good)\b",
            r"\bcompare\b",
            r"\bcomparison\b",
            r"\bversus\b",
            r"\bvs\b",
            r"\bbetter\s+returns?\b",
            r"\bhigher\s+returns?\b",
            r"\bmore\s+returns?\b",
            r"\bbest\s+fund\b",
            r"\btop\s+fund\b",
            r"\bdifference\s+between\b"
        ]
        
        # Advisory regex patterns
        self.advisory_patterns = [
            r"\b(?:should|can|could|would|shall)\s+(?:i|we)\s+(?:invest|buy|sell|exit|put\s+money)\b",
            r"\bis\s+it\s+(?:good|safe|worth|wise|profitable|advisable)\b",
            r"\badvice\b",
            r"\brecommend\b",
            r"\brecommendation\b",
            r"\bsuggest\b",
            r"\bsuggestion\b",
            r"\bworth\s+investing\b",
            r"\bgood\s+choice\b",
            r"\bhelp\s+me\s+choose\b"
        ]
        
        # Allowed schemes or general mutual fund keywords to verify relevance (in-scope)
        self.mf_keywords = [
            r"\bmutual\s+funds?\b", r"\bfunds?\b", r"\bschemes?\b", r"\bsip\b", r"\bnav\b",
            r"\baum\b", r"\bexpense\s+ratio\b", r"\bexit\s+load\b", r"\briskometer\b",
            r"\bbenchmark\b", r"\bmanager\b", r"\bportfolio\b", r"\bholdings?\b", r"\bhdfc\b",
            r"\bdefence\b", r"\bgold\b", r"\bmid-cap\b", r"\bsmall\s+cap\b", r"\btop\s+100\b",
            r"\bexit\b", r"\block-in\b", r"\belss\b", r"\btax\b"
        ]

    def route(self, query: str) -> str:
        """Classifies query into FACTUAL, ADVISORY, COMPARATIVE, or OUT_OF_SCOPE."""
        clean_query = query.strip().lower()
        
        # Check for unallowlisted mutual fund brand names to catch out-of-scope queries early
        other_brands = r"\b(sbi|icici|axis|nippon|kotak|mirae|tata|dsp|uti|quant|motilal|parag|ppfas|aditya|birla|sundaram|invesco|canara|robeco|franklin|templeton|hsbc|bandhan|idfc|lic|union|baroda|pnp|shriram|mahindra|taurus|navi|zerodha)\b"
        if re.search(other_brands, clean_query):
            return "OUT_OF_SCOPE"

        
        # 1. Check for Advisory
        for pattern in self.advisory_patterns:
            if re.search(pattern, clean_query):
                return "ADVISORY"
                
        # 2. Check for Comparative
        for pattern in self.comparative_patterns:
            if re.search(pattern, clean_query):
                return "COMPARATIVE"
                
        # 3. Check if completely Out of Scope
        is_relevant = False
        for kw in self.mf_keywords:
            if re.search(kw, clean_query):
                is_relevant = True
                break
        
        if not is_relevant:
            return "OUT_OF_SCOPE"
            
        # 4. Default to FACTUAL
        return "FACTUAL"
