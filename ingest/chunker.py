import re
import json
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class Chunker:
    def __init__(self, max_tokens=400, overlap=50):
        self.max_tokens = max_tokens
        self.overlap = overlap

    def split_text_recursively(self, text):
        """Splits unstructured text into chunks, respecting paragraphs and sentences."""
        paragraphs = text.split("\n")
        chunks = []
        current_chunk = []
        current_len = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_words = para.split()
            para_len = len(para_words)
            
            if current_len + para_len <= self.max_tokens:
                current_chunk.append(para)
                current_len += para_len
            else:
                # Add current chunk if it exists
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    # Calculate overlap
                    overlap_size = 0
                    overlap_chunk = []
                    for p in reversed(current_chunk):
                         p_words = p.split()
                         p_len = len(p_words)
                         if overlap_size + p_len <= self.overlap:
                             overlap_chunk.insert(0, p)
                             overlap_size += p_len
                         else:
                             break
                    current_chunk = overlap_chunk
                    current_len = overlap_size
                
                # If paragraph itself is too large, split by sentences
                if para_len > self.max_tokens:
                    sentences = re.split(r'(?<=[.!?])\s+', para)
                    for sent in sentences:
                        sent_words = sent.split()
                        sent_len = len(sent_words)
                        if current_len + sent_len <= self.max_tokens:
                            current_chunk.append(sent)
                            current_len += sent_len
                        else:
                            if current_chunk:
                                chunks.append(" ".join(current_chunk))
                                current_chunk = []
                                current_len = 0
                            current_chunk.append(sent)
                            current_len = sent_len
                else:
                    current_chunk.append(para)
                    current_len += para_len
                    
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks

    def generate_chunks(self, html_content, scheme_name, source_url, scheme_id):
        """Generates a list of structure-aware semantic chunks for a scheme."""
        soup = BeautifulSoup(html_content, "lxml")
        
        # 1. Parse JSON state data
        next_data_script = soup.find("script", id="__NEXT_DATA__")
        server_data = {}
        if next_data_script:
            try:
                json_data = json.loads(next_data_script.string)
                server_data = json_data.get("props", {}).get("pageProps", {}).get("mfServerSideData", {})
            except Exception as e:
                logger.warning(f"Failed to parse __NEXT_DATA__ in chunker: {e}")

        chunks = []
        
        # 2. Base overview chunk
        nav = server_data.get("nav", "N/A")
        min_sip = server_data.get("min_sip_investment", "N/A")
        aum = server_data.get("aum", "N/A")
        expense_ratio = server_data.get("expense_ratio", "N/A")
        benchmark = server_data.get("benchmark") or server_data.get("benchmark_name") or "N/A"
        
        # Resolve riskometer
        riskometer = "N/A"
        return_stats = server_data.get("return_stats", [])
        if return_stats and isinstance(return_stats, list):
            riskometer = return_stats[0].get("risk", riskometer)
        if riskometer == "N/A" or not riskometer:
            riskometer = server_data.get("nfo_risk", "N/A")
        if riskometer:
            riskometer = str(riskometer).replace(" Riskometer", "").strip()

        overview_text = (
            f"Scheme: {scheme_name} | "
            f"Overview: The Net Asset Value (NAV) is ₹{nav}. The minimum SIP investment is ₹{min_sip}. "
            f"The Assets Under Management (AUM) is ₹{aum} Cr. The expense ratio is {expense_ratio}% (or direct plan charges). "
            f"The risk category (riskometer) is classified as {riskometer}. The benchmark is {benchmark}."
        )
        chunks.append({
            "text": overview_text,
            "metadata": {
                "type": "overview",
                "scheme_id": scheme_id,
                "scheme_name": scheme_name,
                "source_url": source_url
            }
        })
        
        # 3. Indivisible fund manager profile chunks
        mgr_details = server_data.get("fund_manager_details", [])
        if mgr_details and isinstance(mgr_details, list):
            for m in mgr_details:
                if isinstance(m, dict):
                    m_name = m.get("person_name")
                    if m_name:
                        m_edu = m.get("education", "").strip()
                        m_exp = m.get("experience", "").strip()
                        m_date = m.get("date_from", "").strip()
                        
                        manager_chunk_text = (
                            f"Scheme: {scheme_name} | "
                            f"Fund Manager Profile: {m_name}. "
                            f"Tenure: Managing this fund since {m_date}. "
                            f"Education: {m_edu} "
                            f"Experience: {m_exp}"
                        )
                        chunks.append({
                            "text": manager_chunk_text,
                            "metadata": {
                                "type": "fund_manager",
                                "scheme_id": scheme_id,
                                "scheme_name": scheme_name,
                                "source_url": source_url,
                                "manager_name": m_name
                            }
                        })
                        
        # 4. Grouped Holdings chunks (10 holdings per chunk to preserve column context)
        holdings = server_data.get("holdings", [])
        if holdings and isinstance(holdings, list):
            group_size = 10
            for index in range(0, len(holdings), group_size):
                group = holdings[index:index+group_size]
                holdings_lines = []
                for i, h in enumerate(group, start=index+1):
                    h_name = h.get("company_name", "N/A")
                    h_sector = h.get("sector_name", "N/A")
                    h_inst = h.get("instrument_name", "N/A")
                    h_asset = h.get("corpus_per", 0)
                    holdings_lines.append(f"{i}. {h_name} ({h_sector}, {h_inst}) - {h_asset}% of portfolio assets")
                
                holdings_chunk_text = (
                    f"Scheme: {scheme_name} | "
                    f"Section: Top Holdings (Companies {index+1} to {index+len(group)}) | "
                    f"{' | '.join(holdings_lines)}"
                )
                chunks.append({
                    "text": holdings_chunk_text,
                    "metadata": {
                        "type": "holdings",
                        "scheme_id": scheme_id,
                        "scheme_name": scheme_name,
                        "source_url": source_url,
                        "range": f"{index+1}-{index+len(group)}"
                    }
                })

        # 5. Clean unstructured text paragraphs
        # Decompose script, style, nav, footer, header elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
            
        lines = (line.strip() for line in soup.get_text().splitlines())
        phrases = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in phrases if chunk)
        
        # Split the text recursively
        raw_text_chunks = self.split_text_recursively(clean_text)
        for i, text_chunk in enumerate(raw_text_chunks):
            # Prepend the scheme name to ensure semantic anchor
            prefixed_text = f"Scheme: {scheme_name} | Content:\n{text_chunk}"
            chunks.append({
                "text": prefixed_text,
                "metadata": {
                    "type": "unstructured_text",
                    "scheme_id": scheme_id,
                    "scheme_name": scheme_name,
                    "source_url": source_url,
                    "chunk_index": i
                }
            })
            
        return chunks
