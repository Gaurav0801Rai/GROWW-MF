# Implementation Plan: Mutual Fund FAQ Assistant

This document outlines the phase-wise implementation plan for building the **Facts-Only Mutual Fund FAQ Assistant** based on [problemStatement.md](file:///c:/Users/Gaurav%20Kumar/Desktop/MF-CHATBOT/docs/problemStatement.md) and [architecture.md](file:///c:/Users/Gaurav%20Kumar/Desktop/MF-CHATBOT/docs/architecture.md).

---

## Phase 1: Environment Setup & Scraping Engine (Ingestion Phase 1)
**Goal**: Establish the allowlisted registry and implement the raw HTML scraping mechanism.

### Key Milestones:
1. Set up python virtual environment and configure core dependencies (`requests`, `beautifulsoup4`, `lxml`, `pydantic`, `python-dotenv`).
2. Create `ingest/registry.json` list of the 5 allowed HDFC mutual fund URLs.
3. Write `ingest/scraper.py` to fetch, rate-limit, and save raw HTML locally.
4. Implement basic unit tests for the scraper using mocked HTTP requests.

---

## Phase 2: Parser & Structured Facts Store (Ingestion Phase 2)
**Goal**: Extract clean text, nested tables, and JSON metadata from the crawled pages.

### Key Milestones:
1. Write `ingest/parser.py` to extract:
   * **Structured Facts**: NAV, Minimum SIP, AUM, Expense Ratio, Benchmark, Riskometer, and Fund Managers (with tenure and education).
   * **Unstructured Text**: Main body contents and section tables.
2. Store extracted structured facts to `data/structured/latest/facts.json`.
3. Verify extraction accuracy against all 5 target Groww pages.

---

## Phase 3: Chunking, Local Vector Store Setup (Ingestion Phase 3)
**Goal**: Set up local embedding generation and Chroma DB indexing.

### Key Milestones:
1. Integrate `sentence-transformers` running the `BAAI/bge-small-en-v1.5` (384 dimensions) embedding model.
2. Implement structure-aware semantic chunking logic (300–450 tokens):
   * **Boilerplate Filtering**: Strip out header, footer, and navigation UI links.
   * **Contextual Prepending**: Prepend the scheme name to every chunk (e.g. `Scheme: [Name] | [Content]`).
   * **Indivisible Manager Profiles**: Keep each manager's name, education, and experience together in one chunk.
   * **Table Serialization**: Convert table rows (e.g. holdings, historic returns) into readable text strings that include headers to preserve column relations.
   * **Text Paragraphs**: Use a recursive character text splitter (300–450 tokens with 50–75 tokens overlap).
3. Connect and configure `chromadb` local persistent store under `data/chroma/`.
4. Build `ingest/pipeline.py` to orchestrate scraper -> parser -> chunker -> Chroma upsert.
5. Create `.github/workflows/ingest.yml` running daily at 10:00 AM IST (04:30 UTC) to execute this pipeline.

### Design Decisions:
* **Vector Database (ChromaDB vs FAISS)**: **ChromaDB** is selected because it natively supports document metadata filtering (crucial to restrict searches to specific schemes), is self-contained as a local filesystem database, and integrates seamlessly in Python. FAISS is built for millions of vectors and lacks metadata query and document persistence out-of-the-box.
* **Embedding Model (BGE-small vs BGE-large/Paid)**: **BGE-small-en-v1.5** is chosen because it is free, runs locally, and uses only ~130MB of RAM. BGE-large requires ~1.5GB of RAM, risking Out-Of-Memory (OOM) crashes on basic Render web hosting tiers, and paid APIs (like OpenAI) introduce operational costs.

---

## Phase 4: Intent Router & Safety Refusal Layer (Runtime Phase 1)
**Goal**: Gate incoming queries to filter out non-factual or advisory inputs.

### Key Milestones:
1. Build `runtime/phase_7_safety/router.py`:
   * Implement keyword-based classification and prompt heuristics to identify advisory (e.g. *"Should I invest..."*) and comparative (e.g. *"Which is better..."*) questions.
2. Implement safety refusal responses in `runtime/phase_7_safety/refuser.py` that return polite refusals accompanied by the standard AMFI investor education link.
3. Add tests with mock user inputs to verify classification accuracy.

---

## Phase 5: Semantic Retrieval & Generation (Runtime Phase 2)
**Goal**: Fetch relevant context and draft short, citation-backed factual responses.

### Key Milestones:
1. Implement `runtime/phase_5_retrieval/retriever.py` utilizing a **Metadata-Routed Hybrid Retrieval** strategy:
   * **Entity & Intent Detection**: Identify which of the 5 schemes the query targets and if it seeks specific structured facts (NAV, AUM, etc.).
   * **Path A (Structured Facts)**: Direct lookup from `facts.json` for exact metrics to ensure 100% precision.
   * **Path B (Semantic Search)**: Query Chroma DB with local `bge-small` embeddings using strict metadata filters (e.g. `where={"scheme_id": matched_scheme_id}`) to isolate context and prevent cross-fund pollution.
   * **Context Aggregation**: Combine the structured lookup fact (if any) and the top-k retrieved text chunks into a unified context block.
2. Build the Generation module using the **Groq API** (Llama 3 model) with strict instructions to restrict generation only to the supplied context.
3. Enforce output formatting rules:
   * Max 3 sentences.
   * Exactly one source URL markdown citation.
   * Last updated footer displaying crawl date.

---

## Phase 6: Post-Generation Guardrails & Validation (Runtime Phase 3)
**Goal**: Enforce compliance checking on the model's responses.

### Key Milestones:
1. Build `runtime/phase_7_safety/guards.py` to run programmatic validations:
   * Verify sentence count is `<= 3`.
   * Validate that the response contains **exactly one** markdown link, and that this link belongs to the allowlisted 5 URLs.
   * Run regex/keyword checks to filter out prohibited financial advisory keywords (*"recommend"*, *"better returns"*, etc.).
2. Implement self-correction logic (1 retry with strict prompt redirection) and fall back to a static pre-formatted response containing the scheme's main link on consecutive failures.

---

## Phase 7: Session Memory & API layer (Runtime Phase 4)
**Goal**: Enable multi-thread conversations and expose FastAPI endpoints.

### Key Milestones:
1. Create SQLite thread store (`runtime/phase_8_threads/`) to track conversation history per session (`thread_id`).
2. Add query expansion rules that contextualize current user messages using the last 4-6 thread history entries.
3. Implement `runtime/phase_9_api/app.py` using FastAPI with endpoints:
   * `POST /threads` - Start a thread
   * `GET /threads/{id}/messages` - List messages
   * `POST /threads/{id}/messages` - Send a message and fetch RAG reply
   * `GET /health` - Liveness probe

---

## Phase 8: Frontend UI (Next.js) & Integration
**Goal**: Provide a clean, minimal interface styled with Vanilla CSS.

### Key Milestones:
1. Design Next.js frontend UI (`web/`) matching the visual guidelines:
   * Dark mode interface with dynamic animations.
   * Multi-chat thread sidebar.
   * Disclaimer card (**"Facts-only. No investment advice."**).
   * 3 clickable example query prompts to guide the user.
2. Integrate Next.js client to query the FastAPI backend.
3. Complete manual verification and deploy the frontend to Vercel and the backend to Render.
