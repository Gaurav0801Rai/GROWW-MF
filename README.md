# Mutual Fund FAQ Assistant (Facts-Only Q&A)

An intelligent, compliance-aware Retrieval-Augmented Generation (RAG) assistant built to answer objective, factual questions about mutual fund schemes using **Groww** as the product context. 

The assistant strictly retrieves information from official public sources, enforces a facts-only constraint (no investment advice or recommendations), and cites source URLs under strict compliance guidelines.

---

## 📹 Demo & Screen Recording
A walkthrough demo of the chat interface, factual query retrievals, and compliance safety refusal flows can be found in the root directory:
*   [**MF-CHATBOT.mp4**](./MF-CHATBOT.mp4)

---

## 🌟 Key Features
*   **Facts-Only Q&A:** Answers objective queries like NAV, AUM, exit load, minimum SIP, riskometer, and fund manager profiles (managers, education, tenure).
*   **Strict Regulatory Refusals:** Automatically routes and refuses advisory (e.g. *"Should I invest?"*) or comparative (e.g. *"Which fund is better?"*) inputs, redirecting the user to official investor education links.
*   **Programmatic Guardrails:** Post-generation safety checkers ensure answers are $\le$ 3 sentences, contain exactly one verified canonical link, and have no advisory keywords.
*   **Multi-Thread Memory:** Supports parallel chat session threads with SQLite history tracking.
*   **Sleek Dark Mode UI:** Built with Next.js and Vanilla CSS, featuring smooth hover states and interactive guided prompts.

---

## 📋 Allowlisted HDFC Schemes
The assistant is restricted to retrieving data from the following official Groww URLs:
1.  [HDFC Mid-Cap Opportunities Fund Direct Growth](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth)
2.  [HDFC Top 100 Fund Direct Growth](https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth)
3.  [HDFC Small Cap Fund Direct Growth](https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth)
4.  [HDFC Gold ETF Fund of Fund Direct Plan Growth](https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth)
5.  [HDFC Defence Fund Direct Growth](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)

---

## 🏗️ System Architecture

The project decouples ingestion from query resolution to optimize retrieval accuracy and runtime latency:

1.  **Ingestion Pipeline (Offline):** 
    *   Crawls allowlisted HTML pages, parsing precise metrics (NAV, AUM, exit loads) into a **Structured Facts Store (JSON)**.
    *   Chunks clean text into 300-450 tokens and indexes them into a local **Chroma DB** vector store using `BAAI/bge-small-en-v1.5` embeddings.
2.  **Query Runtime (Online):** 
    *   **Intent Router:** Classifies user messages. If advisory, bypasses search and immediately serves a polite SEBI compliance refusal.
    *   **Hybrid Retriever:** Pulls numbers directly from the JSON store and unstructured profiles from Chroma DB.
    *   **Generator & Validator:** Drafts answers using **Groq API (Llama 3)** and validates them through programmatic safety guards before rendering in the **Next.js UI**.

---

## 🚀 Getting Started

### Prerequisites
*   Node.js (v18+)
*   Python 3.10+
*   A Groq API Key

### Backend Setup
1.  Create a Python virtual environment and activate it:
    ```bash
    python -m venv .venv
    .venv\Scripts\activate
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure your environment in `.env` at the root folder:
    ```env
    GROQ_API_KEY=your_groq_api_key_here
    PORT=8000
    API_HOST=127.0.0.1
    ```
4.  Start the FastAPI server:
    ```bash
    python -m runtime.phase_9_api.app
    ```

### Frontend Setup
1.  Navigate to the `web` folder:
    ```bash
    cd web
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
4.  Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## ⚠️ Known Limitations
*   **Daily Sync Frequency:** Scheme metrics are refreshed once daily via ingestion cron scheduler, meaning intra-day NAV market updates are not reflected in real-time.
*   **Scope Restriction:** The assistant only has access to the 5 allowlisted mutual funds. Questions regarding other mutual funds or broader financial metrics will be politely refused.
