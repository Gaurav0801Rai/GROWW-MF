import os
from dotenv import load_dotenv

# Load environment variables from .env file at the workspace root
load_dotenv()

PORT = int(os.getenv("PORT", "8000"))
API_HOST = os.getenv("API_HOST", "127.0.0.1")
INGEST_CHROMA_DIR = os.getenv("INGEST_CHROMA_DIR", "data/chroma")
INGEST_CHROMA_COLLECTION = os.getenv("INGEST_CHROMA_COLLECTION", "mf_faq_chunks")
THREAD_DB_PATH = os.getenv("THREAD_DB_PATH", "data/threads.sqlite3")
FACTS_PATH = os.getenv("INGEST_FACTS_PATH", "data/structured/latest/facts.json")
REGISTRY_PATH = os.getenv("INGEST_REGISTRY_PATH", "ingest/registry.json")
EDUCATIONAL_URL = os.getenv("EDUCATIONAL_URL", "https://www.amfiindia.com/investor-corner/investor-education")
RUNTIME_API_DEBUG = os.getenv("RUNTIME_API_DEBUG", "0") == "1"
