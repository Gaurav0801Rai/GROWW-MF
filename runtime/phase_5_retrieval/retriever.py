import os
import json
import logging
import chromadb
from ingest.pipeline import LocalBGEEmbeddingFunction

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, chroma_dir=None, collection_name=None, facts_path=None, registry_path=None):
        self.chroma_dir = chroma_dir or os.getenv("INGEST_CHROMA_DIR", "data/chroma")
        self.collection_name = collection_name or os.getenv("INGEST_CHROMA_COLLECTION", "mf_faq_chunks")
        self.facts_path = facts_path or os.getenv("INGEST_FACTS_PATH", "data/structured/latest/facts.json")
        self.registry_path = registry_path or "ingest/registry.json"
        
        # Load registry to get standard scheme details
        self.schemes = []
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                self.schemes = json.load(f).get("schemes", [])
                
        # Load structured facts database
        self.facts_db = []
        if os.path.exists(self.facts_path):
            with open(self.facts_path, "r", encoding="utf-8") as f:
                self.facts_db = json.load(f)
                
        # Initialize Chroma DB client and embedding function
        self.chroma_client = None
        self.collection = None
        self.embedding_fn = None

    def _init_chroma(self):
        if self.collection is None:
            self.chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
            self.embedding_fn = LocalBGEEmbeddingFunction()
            self.collection = self.chroma_client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn
            )

    def detect_scheme(self, query: str) -> str:
        """Resolves target scheme_id from the query text."""
        q = query.lower()
        
        # If the query explicitly mentions other mutual fund brands, do not match any HDFC scheme
        other_brands = [
            "sbi", "icici", "axis", "nippon", "kotak", "mirae", "tata", "dsp", "uti", "quant",
            "motilal", "parag", "ppfas", "aditya", "birla", "sundaram", "invesco", "canara",
            "robeco", "franklin", "templeton", "hsbc", "bandhan", "idfc", "lic", "union",
            "baroda", "pnp", "shriram", "mahindra", "taurus", "navi", "zerodha"
        ]
        import re
        for brand in other_brands:
            if re.search(r"\b" + re.escape(brand) + r"\b", q):
                return None
                
        # Keywords mapping for 5 HDFC schemes
        mappings = {
            "hdfc_defence": ["defence", "defense"],
            "hdfc_gold_etf_fof": ["gold", "etf", "fof", "fund of fund"],
            "hdfc_mid_cap_opportunities": ["mid-cap", "mid cap", "midcap", "opportunities"],
            "hdfc_small_cap": ["small cap", "small-cap", "smallcap"],
            "hdfc_top_100": ["top 100", "top100", "large cap", "large-cap", "largecap", "top hundred"]
        }
        
        # Priority mapping: check longest patterns first
        for scheme_id, keywords in mappings.items():
            for kw in keywords:
                if kw in q:
                    return scheme_id
        return None

    def detect_metric(self, query: str) -> str:
        """Resolves target metric key from the query text."""
        q = query.lower()
        
        mappings = {
            "nav": ["nav", "net asset value"],
            "minimum_sip": ["minimum sip", "min sip", "sip investment", "sip amount", "sip"],
            "fund_size_aum": ["fund size", "aum", "assets under management", "corpus"],
            "expense_ratio": ["expense ratio", "expense", "charges"],
            "riskometer": ["riskometer", "risk category", "risk rating", "risk"],
            "benchmark": ["benchmark", "benchmark index"],
            "fund_managers": ["manager", "managers", "who manages", "managed by", "management team"]
        }
        
        # Check longest keywords first
        for metric, keywords in mappings.items():
            for kw in keywords:
                if kw in q:
                    return metric
        return None

    def retrieve(self, query: str) -> dict:
        """Performs Metadata-Routed Hybrid Retrieval."""
        scheme_id = self.detect_scheme(query)
        metric = self.detect_metric(query)
        
        # Resolve canonical metadata if scheme is detected
        scheme_info = None
        for s in self.schemes:
            if s["id"] == scheme_id:
                scheme_info = s
                break
                
        citation_url = scheme_info["url"] if scheme_info else "https://www.amfiindia.com"
        fetched_at = None
        
        # Load facts for the specific scheme if available
        scheme_facts = None
        for f in self.facts_db:
            if f["scheme_id"] == scheme_id:
                scheme_facts = f
                fetched_at = f.get("fetched_at")
                break
                
        # Path A: Structured Facts Lookup (High-Priority)
        if scheme_facts and metric:
            val = scheme_facts.get(metric)
            if val:
                # Format the structured fact into clear context
                metric_display = metric.replace("_", " ").title()
                if metric == "nav":
                    metric_display = "Net Asset Value (NAV)"
                elif metric == "fund_size_aum":
                    metric_display = "Assets Under Management (AUM)"
                elif metric == "minimum_sip":
                    metric_display = "Minimum SIP Amount"
                
                # Format managers nicely if it's a list
                if isinstance(val, list):
                    val_str = ", ".join(val)
                else:
                    val_str = str(val)
                    
                context_str = (
                    f"Fact: The {metric_display} of {scheme_facts['scheme_name']} is {val_str}. "
                    f"Source Link: {scheme_facts['source_url']}"
                )
                
                return {
                    "context": context_str,
                    "citation_url": scheme_facts["source_url"],
                    "fetched_at": fetched_at,
                    "is_structured": True,
                    "scheme_id": scheme_id
                }
                
        # Path B: Semantic Vector Search
        # Initialize Chroma DB client on demand
        try:
            self._init_chroma()
        except Exception as e:
            logger.error(f"Failed to connect to Chroma DB: {e}")
            # If Chroma DB fails, return structured lookup if possible, or fallback
            if scheme_facts:
                return {
                    "context": f"Fact: Scheme overview for {scheme_facts['scheme_name']}. NAV: {scheme_facts.get('nav')}, AUM: {scheme_facts.get('fund_size_aum')}.",
                    "citation_url": scheme_facts["source_url"],
                    "fetched_at": fetched_at,
                    "is_structured": True,
                    "scheme_id": scheme_id
                }
            return {
                "context": "No context available.",
                "citation_url": citation_url,
                "fetched_at": None,
                "is_structured": False,
                "scheme_id": scheme_id
            }
            
        # Build strict metadata filters if scheme is resolved
        where_filter = {}
        if scheme_id:
            where_filter = {"scheme_id": scheme_id}
            
        # Execute query
        results = self.collection.query(
            query_texts=[query],
            n_results=3,
            where=where_filter
        )
        
        # Combine retrieved chunks
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        
        # Resolve citation and fetched_at from the top chunk metadata
        if metadatas:
            top_meta = metadatas[0]
            if top_meta.get("source_url"):
                citation_url = top_meta["source_url"]
            # If fetched_at is not resolved, try to get from first scheme facts
            if not fetched_at and scheme_facts:
                fetched_at = scheme_facts.get("fetched_at")
                
        context_str = "\n\n".join(docs) if docs else "No relevant context found."
        
        return {
            "context": context_str,
            "citation_url": citation_url,
            "fetched_at": fetched_at,
            "is_structured": False,
            "scheme_id": scheme_id
        }
