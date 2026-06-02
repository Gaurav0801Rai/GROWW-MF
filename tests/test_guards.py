import pytest
from unittest.mock import patch, MagicMock
from runtime.phase_7_safety.guards import ResponseGuard

def test_guard_validation_success(tmp_path):
    # Mock registry file
    registry_path = tmp_path / "registry.json"
    registry_data = {
        "schemes": [
            {"id": "hdfc_defence", "url": "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth"}
        ]
    }
    with open(registry_path, "w", encoding="utf-8") as f:
        json_data = registry_data
        import json
        json.dump(json_data, f)
        
    guard = ResponseGuard(registry_path=str(registry_path))
    
    # Valid response: 2 sentences, 1 allowed link, no prohibited words
    valid_resp = (
        "HDFC Defence Fund Direct Growth has a NAV of ₹28.226. "
        "The minimum SIP amount is ₹100. "
        "[HDFC Defence Fund](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    is_valid, reason = guard.validate(valid_resp)
    assert is_valid is True
    assert reason == "Valid"

def test_guard_validation_prohibited_keywords(tmp_path):
    guard = ResponseGuard(registry_path=str(tmp_path / "nonexistent.json"))
    
    # Contains "recommend"
    invalid_resp = (
        "I recommend that you invest in HDFC Defence Fund. "
        "[Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    is_valid, reason = guard.validate(invalid_resp)
    assert is_valid is False
    assert "Advisory keyword violation" in reason

def test_guard_validation_sentence_count(tmp_path):
    guard = ResponseGuard(registry_path=str(tmp_path / "nonexistent.json"))
    
    # Contains 4 sentences in body
    invalid_resp = (
        "HDFC Defence Fund is a mutual fund. It was launched in 2023. "
        "It has a high risk profile. It has performed very well. "
        "[Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    is_valid, reason = guard.validate(invalid_resp)
    assert is_valid is False
    assert "Sentence count violation" in reason

def test_guard_validation_link_count(tmp_path):
    guard = ResponseGuard(registry_path=str(tmp_path / "nonexistent.json"))
    
    # Contains 2 links
    two_links = (
        "NAV of HDFC Defence is ₹28.226. [Link 1](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth) "
        "and [Link 2](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    is_valid, reason = guard.validate(two_links)
    assert is_valid is False
    assert "Link count violation" in reason
    
    # Contains 0 links
    no_links = (
        "NAV of HDFC Defence is ₹28.226.\n\n"
        "Last updated from sources: 2026-06-02"
    )
    is_valid, reason = guard.validate(no_links)
    assert is_valid is False
    assert "Link count violation" in reason

def test_guard_validation_url_allowlist(tmp_path):
    guard = ResponseGuard(registry_path=str(tmp_path / "nonexistent.json"))
    
    # URL not in the default allowlist
    bad_url = (
        "NAV of HDFC Defence is ₹28.226. [Link](https://somebadurl.com/scheme)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    is_valid, reason = guard.validate(bad_url)
    assert is_valid is False
    assert "URL violation" in reason

def test_execute_with_correction_success_first_try(tmp_path):
    guard = ResponseGuard(registry_path=str(tmp_path / "nonexistent.json"))
    
    mock_generator = MagicMock()
    valid_resp = (
        "NAV of HDFC Defence is ₹28.226. [Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    mock_generator.generate.return_value = valid_resp
    
    result = guard.execute_with_correction(
        generator=mock_generator,
        query="NAV of HDFC Defence?",
        context="NAV is ₹28.226",
        citation_url="https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth"
    )
    
    assert result == valid_resp
    assert mock_generator.generate.call_count == 1

def test_execute_with_correction_success_retry(tmp_path):
    guard = ResponseGuard(registry_path=str(tmp_path / "nonexistent.json"))
    
    mock_generator = MagicMock()
    invalid_resp = "I recommend this fund. [Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)"
    valid_resp = (
        "NAV of HDFC Defence is ₹28.226. [Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)\n\n"
        "Last updated from sources: 2026-06-02"
    )
    mock_generator.generate.side_effect = [invalid_resp, valid_resp]
    
    result = guard.execute_with_correction(
        generator=mock_generator,
        query="NAV of HDFC Defence?",
        context="NAV is ₹28.226",
        citation_url="https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth"
    )
    
    assert result == valid_resp
    assert mock_generator.generate.call_count == 2

def test_execute_with_correction_fallback(tmp_path):
    # Mock registry
    registry_path = tmp_path / "registry.json"
    registry_data = {
        "schemes": [
            {"id": "hdfc_defence", "name": "HDFC Defence Fund Direct Growth", "url": "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth"}
        ]
    }
    with open(registry_path, "w", encoding="utf-8") as f:
        import json
        json.dump(registry_data, f)
        
    guard = ResponseGuard(registry_path=str(registry_path))
    
    mock_generator = MagicMock()
    invalid_resp1 = "I recommend this fund. [Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)"
    invalid_resp2 = "This is a good choice. [Link](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)"
    mock_generator.generate.side_effect = [invalid_resp1, invalid_resp2]
    
    result = guard.execute_with_correction(
        generator=mock_generator,
        query="NAV of HDFC Defence?",
        context="NAV is ₹28.226",
        citation_url="https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
        fetched_at="2026-06-02T12:00:00Z"
    )
    
    assert "Here is the official information regarding the HDFC Defence Fund Direct Growth" in result
    assert "[HDFC Defence Fund Direct Growth](https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth)" in result
    assert "Last updated from sources: 2026-06-02" in result
    assert mock_generator.generate.call_count == 2
