import os
import json
import pytest
from unittest.mock import patch, MagicMock
from ingest.scraper import Scraper

def test_load_registry(tmp_path):
    # Create a temp registry file
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {"id": "test_fund", "name": "Test Fund", "url": "https://example.com/test"}
        ]
    }
    registry_file = tmp_path / "registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    scraper = Scraper(registry_path=str(registry_file))
    data = scraper.load_registry()
    assert data["amc"] == "HDFC Mutual Fund"
    assert len(data["schemes"]) == 1

@patch("ingest.scraper.requests.get")
@patch("ingest.scraper.time.sleep")
def test_scrape_all_success(mock_sleep, mock_get, tmp_path):
    # Setup mock registry
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {"id": "scheme1", "name": "Scheme 1", "url": "https://example.com/1"},
            {"id": "scheme2", "name": "Scheme 2", "url": "https://example.com/2"}
        ]
    }
    registry_file = tmp_path / "registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    # Setup scraper
    output_dir = tmp_path / "data/raw"
    scraper = Scraper(registry_path=str(registry_file), output_dir=str(output_dir))
    
    # Mock requests.get response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html>Test Content</html>"
    mock_get.return_value = mock_resp
    
    manifest, run_dir = scraper.scrape_all()
    
    # Assertions
    assert os.path.exists(run_dir)
    assert os.path.exists(os.path.join(run_dir, "manifest.json"))
    assert os.path.exists(os.path.join(run_dir, "scheme1.html"))
    assert os.path.exists(os.path.join(run_dir, "scheme2.html"))
    
    # Verify content saved
    with open(os.path.join(run_dir, "scheme1.html"), "r", encoding="utf-8") as f:
        assert f.read() == "<html>Test Content</html>"
        
    # Verify manifest details
    assert manifest["run_id"] is not None
    assert len(manifest["results"]) == 2
    assert manifest["results"][0]["scheme_id"] == "scheme1"
    assert manifest["results"][0]["status"] == "success"
    
    # Verify rate limiter was called
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(2.0)

@patch("ingest.scraper.requests.get")
@patch("ingest.scraper.time.sleep")
def test_scrape_all_failure(mock_sleep, mock_get, tmp_path):
    # Setup mock registry
    registry_data = {
        "amc": "HDFC Mutual Fund",
        "schemes": [
            {"id": "scheme1", "name": "Scheme 1", "url": "https://example.com/1"},
            {"id": "scheme2", "name": "Scheme 2", "url": "https://example.com/2"}
        ]
    }
    registry_file = tmp_path / "registry.json"
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry_data, f)
        
    # Setup scraper
    output_dir = tmp_path / "data/raw"
    scraper = Scraper(registry_path=str(registry_file), output_dir=str(output_dir))
    
    # Mock requests.get failure for the first request, success for the second
    mock_resp_success = MagicMock()
    mock_resp_success.status_code = 200
    mock_resp_success.text = "<html>Success</html>"
    
    mock_get.side_effect = [Exception("Connection timeout"), mock_resp_success]
    
    manifest, run_dir = scraper.scrape_all()
    
    # Assertions
    assert os.path.exists(run_dir)
    assert os.path.exists(os.path.join(run_dir, "manifest.json"))
    assert not os.path.exists(os.path.join(run_dir, "scheme1.html"))
    assert os.path.exists(os.path.join(run_dir, "scheme2.html"))
    
    # Verify manifest details
    assert len(manifest["results"]) == 2
    assert manifest["results"][0]["scheme_id"] == "scheme1"
    assert manifest["results"][0]["status"] == "failed"
    assert "Connection timeout" in manifest["results"][0]["error"]
    
    assert manifest["results"][1]["scheme_id"] == "scheme2"
    assert manifest["results"][1]["status"] == "success"
