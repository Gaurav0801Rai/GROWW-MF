import os
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from runtime.phase_9_api.app import app
import runtime.phase_9_api.config as config

@pytest.fixture
def client(tmp_path):
    # Set a temp thread database path for API during tests
    temp_db = tmp_path / "threads.sqlite3"
    with patch.dict(os.environ, {"THREAD_DB_PATH": str(temp_db)}):
        from runtime.phase_9_api import app as api_module
        api_module.thread_store = api_module.ThreadStore(db_path=str(temp_db))
        
        # Mock generator to avoid real Groq API calls during tests
        api_module.generator = MagicMock()
        api_module.query_expander = api_module.QueryExpander(generator=api_module.generator)
        api_module.guard = api_module.ResponseGuard(registry_path=config.REGISTRY_PATH)
        
        with TestClient(app) as test_client:
            yield test_client

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_thread_lifecycle(client):
    # 1. Create a thread
    response = client.post("/threads")
    assert response.status_code == 200
    data = response.json()
    assert "thread_id" in data
    thread_id = data["thread_id"]
    
    # 2. Get messages for the new thread (should be empty)
    response = client.get(f"/threads/{thread_id}/messages")
    assert response.status_code == 200
    assert response.json() == []

@patch("runtime.phase_9_api.app.retriever")
def test_post_factual_message(mock_retriever, client):
    # 1. Create a thread
    thread_resp = client.post("/threads").json()
    thread_id = thread_resp["thread_id"]
    
    # Mock Retriever output
    mock_retriever.retrieve.return_value = {
        "context": "Fact: The NAV of HDFC Mid-Cap is ₹218.882.",
        "citation_url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
        "fetched_at": "2026-06-02T12:00:00Z",
        "is_structured": True,
        "scheme_id": "hdfc_mid_cap_opportunities"
    }
    
    # Mock Generator output
    from runtime.phase_9_api import app as api_module
    api_module.generator.generate.return_value = (
        "HDFC Mid-Cap Opportunities Fund NAV is ₹218.882. "
        "[HDFC Mid-Cap](https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    
    # 2. Post factual message
    response = client.post(
        f"/threads/{thread_id}/messages",
        json={"content": "What is the NAV of HDFC Mid-Cap?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert "₹218.882" in data["content"]
    assert "Last updated from sources: 2026-06-02" in data["content"]
    assert data["citation_url"] == "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
    
    # 3. Check thread messages (should contain 2 messages: user and assistant)
    history = client.get(f"/threads/{thread_id}/messages").json()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"

def test_post_advisory_message(client):
    # 1. Create a thread
    thread_id = client.post("/threads").json()["thread_id"]
    
    # 2. Post advisory message
    response = client.post(
        f"/threads/{thread_id}/messages",
        json={"content": "Should I invest in HDFC Small Cap Fund?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert "cannot provide investment advice" in data["content"]

def test_post_comparative_message(client):
    # 1. Create a thread
    thread_id = client.post("/threads").json()["thread_id"]
    
    # 2. Post comparative message
    response = client.post(
        f"/threads/{thread_id}/messages",
        json={"content": "Which is better: HDFC Mid-cap or HDFC Top 100?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert "cannot compare different mutual fund schemes" in data["content"]
