import os
import json
import time
import logging
import requests
from datetime import datetime, timezone

# Set up basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class Scraper:
    def __init__(self, registry_path="ingest/registry.json", output_dir="data/raw"):
        self.registry_path = registry_path
        self.output_dir = output_dir
        self.headers = {
            "User-Agent": os.getenv("INGEST_USER_AGENT", "MutualFundFAQBot/1.0 (Facts-Only QA Assistant)"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        }
        self.rate_limit_seconds = float(os.getenv("INGEST_RATE_LIMIT_SECONDS", "2.0"))

    def load_registry(self):
        if not os.path.exists(self.registry_path):
            raise FileNotFoundError(f"Registry file not found at {self.registry_path}")
        with open(self.registry_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def scrape_all(self):
        registry = self.load_registry()
        schemes = registry.get("schemes", [])
        
        # Create a unique run timestamp directory
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join(self.output_dir, run_id)
        os.makedirs(run_dir, exist_ok=True)
        
        manifest = {
            "run_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": []
        }
        
        logger.info(f"Starting scraping run: {run_id}")
        
        for scheme in schemes:
            scheme_id = scheme["id"]
            url = scheme["url"]
            name = scheme["name"]
            
            logger.info(f"Fetching URL for {name}: {url}")
            
            try:
                # Respect rate limit
                time.sleep(self.rate_limit_seconds)
                
                response = requests.get(url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                # Save raw HTML content
                file_name = f"{scheme_id}.html"
                file_path = os.path.join(run_dir, file_name)
                
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(response.text)
                
                logger.info(f"Successfully scraped and saved {name} to {file_path}")
                manifest["results"].append({
                    "scheme_id": scheme_id,
                    "name": name,
                    "url": url,
                    "status": "success",
                    "file_path": file_path,
                    "response_code": response.status_code
                })
                
            except Exception as e:
                logger.error(f"Failed to scrape {name}: {e}")
                manifest["results"].append({
                    "scheme_id": scheme_id,
                    "name": name,
                    "url": url,
                    "status": "failed",
                    "error": str(e)
                })
        
        # Write run manifest
        manifest_path = os.path.join(run_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Finished scraping run. Manifest saved to {manifest_path}")
        return manifest, run_dir

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    scraper = Scraper()
    scraper.scrape_all()
