import os
import json
import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from ingest.pipeline import IngestionPipeline, LocalBGEEmbeddingFunction

def test_local_bge_embedding_function():
    # Test that the embedding function returns a list of items of dimension 384
    fn = LocalBGEEmbeddingFunction()
    docs = ["HDFC Mutual Fund", "Top 100 Scheme Direct Growth"]
    embeddings = fn(docs)
    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384

@patch("ingest.pipeline.Scraper")
def test_pipeline_run(mock_scraper_class, tmp_path):
    run_id = "20260602_120000"
    raw_dir = tmp_path / "raw"
    run_dir = raw_dir / run_id
    os.makedirs(run_dir)

    # Setup mock scraper instance and returns
    mock_scraper = MagicMock()
    mock_scraper.scrape_all.return_value = (
        {"run_id": run_id, "timestamp": "2026-06-02T12:00:00Z"},
        str(run_dir)
    )
    mock_scraper_class.return_value = mock_scraper
    
    # Mock Next.js HTML content
    mock_html = """
    <html>
      <script id="__NEXT_DATA__" type="application/json">
        {
          "props": {
            "pageProps": {
              "mfServerSideData": {
                "nav": 150.5,
                "min_sip_investment": 100,
                "aum": 12000.5,
                "expense_ratio": "0.75",
                "benchmark": "Nifty 50 TRI",
                "nfo_risk": "Very High",
                "fund_manager_details": [
                  {
                    "person_name": "Test Manager",
                    "education": "MBA",
                    "experience": "10 years",
                    "date_from": "2020-01-01"
                  }
                ],
                "holdings": [
                  {
                    "company_name": "Company A",
                    "sector_name": "Tech",
                    "instrument_name": "Equity",
                    "corpus_per": 5.5
                  }
                ]
              }
            }
          }
        }
      </script>
      <body>Mutual Fund Page</body>
    </html>
    """
    
    with open(run_dir / "hdfc_mid_cap_opportunities.html", "w", encoding="utf-8") as f:
        f.write(mock_html)
        
    # Mock registry.json
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {
                "id": "hdfc_mid_cap_opportunities",
                "name": "HDFC Mid-Cap Opportunities Fund Direct Growth",
                "url": "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth"
            }
        ]
    }
    registry_path = tmp_path / "registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    # Initialize pipeline
    chroma_dir = tmp_path / "chroma"
    facts_path = tmp_path / "structured/latest/facts.json"
    
    # Initialize pipeline passing the configurable facts_path
    pipeline = IngestionPipeline(
        registry_path=str(registry_path),
        raw_dir=str(raw_dir),
        chroma_dir=str(chroma_dir),
        collection_name="test_collection",
        facts_path=str(facts_path)
    )
    
    # Run pipeline (forcing mock scrape)
    num_indexed = pipeline.run(skip_scrape=False)
    
    # Verify execution outputs
    assert num_indexed > 0
    assert os.path.exists(raw_dir)
    assert os.path.exists(chroma_dir)
    assert os.path.exists(facts_path)
    
    # Check facts file content
    with open(facts_path, "r", encoding="utf-8") as f:
        facts = json.load(f)
        assert len(facts) == 1
        assert facts[0]["scheme_id"] == "hdfc_mid_cap_opportunities"
        assert facts[0]["nav"] == "₹150.5"
        assert facts[0]["minimum_sip"] == "₹100"
        assert facts[0]["fund_size_aum"] == "₹12,000.50 Cr"
