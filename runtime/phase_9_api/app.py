import os
import logging
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import runtime.phase_9_api.config as config
from runtime.phase_8_threads.store import ThreadStore
from runtime.phase_8_threads.expander import QueryExpander
from runtime.phase_7_safety.router import IntentRouter
from runtime.phase_7_safety.refuser import SafetyRefuser
from runtime.phase_7_safety.guards import ResponseGuard
from runtime.phase_5_retrieval.retriever import Retriever
from runtime.phase_5_retrieval.generator import Generator

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="Mutual Fund FAQ Assistant API",
    description="Facts-Only Q&A Assistant API for HDFC Mutual Funds",
    version="1.0.0"
)

# Enable CORS for Next.js frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Components
logger.info("Initializing RAG runtime components...")
thread_store = ThreadStore(db_path=config.THREAD_DB_PATH)
router = IntentRouter()
refuser = SafetyRefuser()
guard = ResponseGuard(registry_path=config.REGISTRY_PATH)
retriever = Retriever(
    chroma_dir=config.INGEST_CHROMA_DIR,
    collection_name=config.INGEST_CHROMA_COLLECTION,
    facts_path=config.FACTS_PATH,
    registry_path=config.REGISTRY_PATH
)
generator = Generator()
query_expander = QueryExpander(generator=generator)
logger.info("RAG runtime components initialized successfully.")

# Request/Response Pydantic Schemas
class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, description="The user's query content")

class MessageResponse(BaseModel):
    id: str
    thread_id: str
    role: str
    content: str
    timestamp: str
    citation_url: str | None = None

class ThreadResponse(BaseModel):
    thread_id: str

@app.get("/health")
def health_check():
    """Liveness probe endpoint."""
    return {"status": "ok"}

@app.get("/metadata")
def get_metadata():
    """Returns dataset metadata (like latest data refresh/crawl timestamp)."""
    import json
    try:
        if os.path.exists(config.FACTS_PATH):
            with open(config.FACTS_PATH, "r", encoding="utf-8") as f:
                facts = json.load(f)
                if facts:
                    fetched_dates = [item.get("fetched_at") for item in facts if item.get("fetched_at")]
                    if fetched_dates:
                        # Find the max date
                        latest_date = max(fetched_dates)
                        return {
                            "last_updated": latest_date,
                            "source": "official_groww_pages"
                        }
        return {"last_updated": "2026-06-02T16:52:50Z", "source": "verified_sources"}
    except Exception as e:
        logger.error(f"Failed to fetch metadata: {e}")
        return {"last_updated": "2026-06-02T16:52:50Z", "source": "verified_sources"}

@app.post("/threads", response_model=ThreadResponse)
def create_thread():
    """Starts a new chat thread session."""
    try:
        thread_id = thread_store.create_thread()
        logger.info(f"Created new conversation thread: {thread_id}")
        return {"thread_id": thread_id}
    except Exception as e:
        logger.error(f"Failed to create thread: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize session thread.")

@app.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
def get_thread_messages(thread_id: str):
    """Lists messages for a specific conversation session."""
    try:
        messages = thread_store.get_messages(thread_id)
        return messages
    except Exception as e:
        logger.error(f"Failed to fetch messages for thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve thread history.")

@app.post("/threads/{thread_id}/messages", response_model=MessageResponse)
def post_message(thread_id: str, payload: MessageRequest):
    """Sends a user query and returns the RAG assistant response."""
    user_query = payload.content.strip()
    
    # 1. Save user query in the thread history
    try:
        thread_store.add_message(thread_id=thread_id, role="user", content=user_query)
    except Exception as e:
        logger.error(f"Failed to write user message to DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to save message.")
        
    # 2. Retrieve history for query expansion
    try:
        history = thread_store.get_messages(thread_id, limit=6)
        # Drop the last message (which is the user query we just inserted) to get clean history
        history_history = history[:-1] if len(history) > 1 else []
    except Exception as e:
        logger.error(f"Failed to load history: {e}")
        history_history = []
        
    # 3. Contextualize/Expand User Query
    expanded_query = query_expander.expand(user_query, history_history)
    
    # 4. Intent Routing (Pre-Retrieval)
    intent = router.route(expanded_query)
    logger.info(f"Routed query intent for '{expanded_query}': {intent}")
    
    # 5. Handle Refusals Directly (Advisory, Comparative, OOS)
    if intent != "FACTUAL":
        refusal_content = refuser.get_refusal(intent)
        educational_url = refuser.educational_url
        
        # Save refusal response to DB
        assistant_msg = thread_store.add_message(
            thread_id=thread_id,
            role="assistant",
            content=refusal_content,
            citation_url=educational_url
        )
        return assistant_msg
        
    # 6. Path Factual: Run Retriever
    try:
        retrieval_data = retriever.retrieve(expanded_query)
        context = retrieval_data["context"]
        citation_url = retrieval_data["citation_url"]
        fetched_at = retrieval_data["fetched_at"]
    except Exception as e:
        logger.error(f"Retrieval step failed: {e}")
        # Build safe fallback context
        context = "No relevant context found due to internal search failure."
        citation_url = "https://www.amfiindia.com"
        fetched_at = None
        
    # 7. Generate Response with Guardrails
    try:
        # Runs LLM generation with validation, correction, and fallback
        reply_content = guard.execute_with_correction(
            generator=generator,
            query=expanded_query,
            context=context,
            citation_url=citation_url,
            fetched_at=fetched_at
        )
    except Exception as e:
        logger.error(f"Generation step failed: {e}")
        # Static fallback response
        date_str = fetched_at.split("T")[0] if fetched_at else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        reply_content = (
            "An error occurred while generating the answer. "
            f"Please refer to the canonical source page: {citation_url}.\n\n"
            f"Last updated from sources: {date_str}"
        )
        
    # 8. Save assistant reply in thread history
    try:
        assistant_msg = thread_store.add_message(
            thread_id=thread_id,
            role="assistant",
            content=reply_content,
            citation_url=citation_url
        )
        return assistant_msg
    except Exception as e:
        logger.error(f"Failed to write assistant response to DB: {e}")
        raise HTTPException(status_code=500, detail="Failed to save assistant reply.")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting uvicorn server on {config.API_HOST}:{config.PORT}")
    uvicorn.run(
        "runtime.phase_9_api.app:app",
        host=config.API_HOST,
        port=config.PORT,
        reload=config.RUNTIME_API_DEBUG
    )
