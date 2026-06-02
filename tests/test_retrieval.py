import os
import json
import pytest
from unittest.mock import patch, MagicMock
from runtime.phase_5_retrieval.retriever import Retriever
from runtime.phase_5_retrieval.generator import Generator

def test_retriever_detection(tmp_path):
    # Mock registry
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {"id": "hdfc_defence", "name": "HDFC Defence Fund", "url": "https://example.com/1"},
            {"id": "hdfc_mid_cap_opportunities", "name": "HDFC Mid-Cap", "url": "https://example.com/2"}
        ]
    }
    registry_path = tmp_path / "registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    retriever = Retriever(registry_path=str(registry_path), facts_path=str(tmp_path / "facts.json"))
    
    assert retriever.detect_scheme("what is the nav of HDFC Defence?") == "hdfc_defence"
    assert retriever.detect_scheme("Is mid-cap opportunities a good fund?") == "hdfc_mid_cap_opportunities"
    assert retriever.detect_scheme("completely unrelated query") is None
    
    assert retriever.detect_metric("show me the NAV") == "nav"
    assert retriever.detect_metric("who is the manager?") == "fund_managers"
    assert retriever.detect_metric("general question") is None

def test_retriever_structured_lookup(tmp_path):
    # Mock registry and facts.json
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {"id": "hdfc_defence", "name": "HDFC Defence Fund Direct Growth", "url": "https://example.com/1"}
        ]
    }
    registry_path = tmp_path / "registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    facts_data = [
        {
            "scheme_id": "hdfc_defence",
            "scheme_name": "HDFC Defence Fund Direct Growth",
            "source_url": "https://example.com/1",
            "fetched_at": "2026-06-02T12:00:00Z",
            "nav": "₹28.226",
            "minimum_sip": "₹100"
        }
    ]
    facts_path = tmp_path / "facts.json"
    with open(facts_path, "w", encoding="utf-8") as f:
        json.dump(facts_data, f)
        
    retriever = Retriever(
        registry_path=str(registry_path), 
        facts_path=str(facts_path),
        chroma_dir=str(tmp_path / "chroma")
    )
    
    # Run structured retrieval
    result = retriever.retrieve("What is the NAV of HDFC Defence?")
    assert result["is_structured"] is True
    assert "₹28.226" in result["context"]
    assert "Net Asset Value (NAV)" in result["context"]
    assert result["citation_url"] == "https://example.com/1"
    assert result["fetched_at"] == "2026-06-02T12:00:00Z"

@patch("runtime.phase_5_retrieval.retriever.chromadb.PersistentClient")
@patch("runtime.phase_5_retrieval.retriever.LocalBGEEmbeddingFunction")
def test_retriever_semantic_search(mock_embed, mock_chroma, tmp_path):
    # Setup mock registry and facts
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {"id": "hdfc_defence", "name": "HDFC Defence Fund", "url": "https://example.com/1"}
        ]
    }
    registry_path = tmp_path / "registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    # Setup mock Chroma collection
    mock_collection = MagicMock()
    mock_collection.query.return_value = {
        "documents": [["HDFC Defence exit load is 1% if redeemed within 1 year."]],
        "metadatas": [[{"source_url": "https://example.com/1", "scheme_id": "hdfc_defence"}]]
    }
    
    mock_client = MagicMock()
    mock_client.get_collection.return_value = mock_collection
    mock_chroma.return_value = mock_client
    
    retriever = Retriever(
        registry_path=str(registry_path),
        facts_path=str(tmp_path / "facts.json"),
        chroma_dir=str(tmp_path / "chroma")
    )
    
    # Run semantic retrieval
    result = retriever.retrieve("what is the exit load of HDFC Defence?")
    assert result["is_structured"] is False
    assert "exit load is 1%" in result["context"]
    assert result["citation_url"] == "https://example.com/1"
    mock_collection.query.assert_called_once_with(
        query_texts=["what is the exit load of HDFC Defence?"],
        n_results=3,
        where={"scheme_id": "hdfc_defence"}
    )

@patch("runtime.phase_5_retrieval.generator.Groq")
def test_generator(mock_groq_class):
    # Setup mock Groq client response
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    
    mock_message.content = "HDFC Defence Fund's NAV is ₹28.226. [HDFC Defence Fund](https://example.com/1)"
    mock_choice.message = mock_message
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion
    mock_groq_class.return_value = mock_client
    
    # Set fake API key so generator initializes
    with patch.dict(os.environ, {"GROQ_API_KEY": "fake_key"}):
        generator = Generator()
        
    response = generator.generate(
        query="NAV of HDFC Defence?",
        context="NAV is ₹28.226.",
        citation_url="https://example.com/1",
        fetched_at="2026-06-02T12:00:00Z"
    )
    
    assert "₹28.226" in response
    assert "Last updated from sources: 2026-06-02" in response
    assert "https://example.com/1" in response
    mock_client.chat.completions.create.assert_called_once()
