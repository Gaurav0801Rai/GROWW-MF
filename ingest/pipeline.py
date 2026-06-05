import os
import json
import logging
import hashlib
import glob
import requests
import time
from datetime import datetime, timezone
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from ingest.scraper import Scraper
from ingest.parser import Parser
from ingest.chunker import Chunker

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class LocalBGEEmbeddingFunction(EmbeddingFunction):
    """Custom embedding function using Hugging Face Serverless Inference API for BGE model."""
    def __init__(self, model_name="BAAI/bge-small-en-v1.5"):
        self.model_name = model_name
        self.api_url = f"https://router.huggingface.co/hf-inference/models/{model_name}"
        self.headers = {}
        token = os.getenv("HF_TOKEN")
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        logger.info(f"Hugging Face Serverless Inference API initialized for model: {model_name} (Authenticated: {bool(token)})")

    def __call__(self, input: Documents) -> Embeddings:
        payload = {"inputs": input, "options": {"wait_for_model": True}}
        
        # Retry logic for model loading / temporary network glitches
        for attempt in range(3):
            try:
                response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=30)
                if response.status_code == 200:
                    embeddings = response.json()
                    if isinstance(embeddings, list) and len(embeddings) > 0:
                        if not isinstance(embeddings[0], list):
                            embeddings = [embeddings]
                        return embeddings
                    raise ValueError(f"Unexpected HF response format: {embeddings}")
                elif response.status_code == 503:
                    # Model is loading on Hugging Face servers
                    err_json = response.json()
                    estimated_time = err_json.get("estimated_time", 10)
                    logger.warning(f"HF Model is currently loading. Waiting {estimated_time}s (attempt {attempt + 1}/3)...")
                    time.sleep(min(estimated_time, 10))
                else:
                    raise ValueError(f"HF API returned status {response.status_code}: {response.text}")
            except Exception as e:
                logger.error(f"HF embedding generation failed (attempt {attempt + 1}/3): {e}")
                if attempt == 2:
                    raise e
                time.sleep(2)
        raise ValueError("Failed to get embeddings from Hugging Face Inference API.")


class IngestionPipeline:
    def __init__(self, registry_path="ingest/registry.json", raw_dir="data/raw", 
                 chroma_dir="data/chroma", collection_name="mf_faq_chunks",
                 facts_path="data/structured/latest/facts.json"):
        self.registry_path = registry_path
        self.raw_dir = raw_dir
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.facts_path = facts_path
        self.scraper = Scraper(registry_path=registry_path, output_dir=raw_dir)
        self.parser = Parser()
        self.chunker = Chunker()

    def run(self, skip_scrape=False):
        """Runs the complete ingestion pipeline."""
        logger.info("Starting Ingestion Pipeline...")
        
        # 1. Scrape (if not skipped)
        if not skip_scrape:
            logger.info("Step 1/4: Scraping HDFC Mutual Fund pages...")
            manifest, run_dir = self.scraper.scrape_all()
            logger.info(f"Scrape completed. Saved files to: {run_dir}")
        else:
            logger.info("Step 1/4: Skipping scraping. Locating latest run...")
            raw_dirs = sorted(glob.glob(os.path.join(self.raw_dir, "20*")))
            if not raw_dirs:
                raise FileNotFoundError("No scraped runs found. Cannot skip scrape.")
            run_dir = raw_dirs[-1]
            logger.info(f"Using latest raw run directory: {run_dir}")

        # 2. Parse Structured Facts
        logger.info("Step 2/4: Parsing HTML files and saving structured facts...")
        facts = self.parser.parse_latest_raw(
            registry_path=self.registry_path, 
            output_file=self.facts_path,
            raw_dir=self.raw_dir
        )
        if not facts:
            raise ValueError("No facts parsed. Pipeline failed.")
        logger.info(f"Successfully saved structured facts to {self.facts_path}")
        
        # Load registry to map scheme info
        with open(self.registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        schemes = {s["id"]: s for s in registry.get("schemes", [])}

        # 3. Generate Chunks
        logger.info("Step 3/4: Chunking HTML files...")
        all_chunks = []
        html_files = glob.glob(os.path.join(run_dir, "*.html"))
        
        for file_path in html_files:
            scheme_id = os.path.basename(file_path).replace(".html", "")
            scheme_info = schemes.get(scheme_id, {})
            scheme_name = scheme_info.get("name", scheme_id)
            scheme_url = scheme_info.get("url", "")
            
            logger.info(f"Generating chunks for {scheme_name}...")
            with open(file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
                
            scheme_chunks = self.chunker.generate_chunks(
                html_content=html_content,
                scheme_name=scheme_name,
                source_url=scheme_url,
                scheme_id=scheme_id
            )
            all_chunks.extend(scheme_chunks)
            
        logger.info(f"Generated {len(all_chunks)} total chunks across all schemes.")

        # 4. Upsert into Chroma DB
        logger.info("Step 4/4: Upserting chunks into Chroma DB...")
        
        # Initialize local persistent client
        os.makedirs(self.chroma_dir, exist_ok=True)
        chroma_client = chromadb.PersistentClient(path=self.chroma_dir)
        
        # Initialize embedding function
        embedding_fn = LocalBGEEmbeddingFunction()
        
        # Get or create collection
        collection = chroma_client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Prepare batch payloads
        ids = []
        documents = []
        metadatas = []
        
        for chunk in all_chunks:
            chunk_text = chunk["text"]
            chunk_meta = chunk["metadata"]
            
            # Generate a deterministic ID based on the content hash
            chunk_id = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
            
            ids.append(chunk_id)
            documents.append(chunk_text)
            metadatas.append(chunk_meta)
            
        # Upsert in batches of 40k if needed (Chroma limitation check)
        batch_size = 500
        for idx in range(0, len(ids), batch_size):
            end_idx = idx + batch_size
            collection.upsert(
                ids=ids[idx:end_idx],
                documents=documents[idx:end_idx],
                metadatas=metadatas[idx:end_idx]
            )
            
        logger.info(f"Ingestion pipeline completed successfully! {len(ids)} chunks indexed in Chroma collection '{self.collection_name}'.")
        return len(ids)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run the pipeline (default is to skip scrape to save time if raw files exist,
    # but run scrape if force argument is passed)
    import sys
    force_scrape = "--scrape" in sys.argv
    
    pipeline = IngestionPipeline()
    pipeline.run(skip_scrape=not force_scrape)
