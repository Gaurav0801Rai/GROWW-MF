import pytest
from runtime.phase_7_safety.router import IntentRouter
from runtime.phase_7_safety.refuser import SafetyRefuser

def test_intent_router_factual():
    router = IntentRouter()
    
    factual_queries = [
        "What is the NAV of HDFC Mid-Cap Opportunities Fund?",
        "Who is the fund manager of HDFC Top 100?",
        "what is the expense ratio of HDFC Defence?",
        "minimum SIP amount for hdfc gold etf fof",
        "Benchmark of HDFC Small Cap Fund Direct Growth",
        "show me the holdings of HDFC Mid-Cap Opportunities"
    ]
    
    for query in factual_queries:
        assert router.route(query) == "FACTUAL", f"Failed on factual query: {query}"

def test_intent_router_advisory():
    router = IntentRouter()
    
    advisory_queries = [
        "Should I invest in HDFC Mid-Cap?",
        "is it safe to put money in HDFC Small Cap?",
        "Can you suggest if I should buy HDFC Top 100?",
        "Give me some investment advice on HDFC Defence Fund",
        "Is it worth investing in this scheme?",
        "Which fund do you recommend?"
    ]
    
    for query in advisory_queries:
        assert router.route(query) == "ADVISORY", f"Failed on advisory query: {query}"

def test_intent_router_comparative():
    router = IntentRouter()
    
    comparative_queries = [
        "Which is better: HDFC Mid-Cap or HDFC Small Cap?",
        "compare HDFC Top 100 and HDFC Mid-Cap Opportunities",
        "Which fund gives higher returns between Gold and Defence?",
        "what is the difference between HDFC Mid-cap and HDFC Small Cap?",
        "HDFC Top 100 vs HDFC Small Cap"
    ]
    
    for query in comparative_queries:
        assert router.route(query) == "COMPARATIVE", f"Failed on comparative query: {query}"

def test_intent_router_out_of_scope():
    router = IntentRouter()
    
    oos_queries = [
        "What is the weather today?",
        "Who is the President of the United States?",
        "How to write a python script?",
        "Tell me a joke",
        "AAPL stock price"
    ]
    
    for query in oos_queries:
        assert router.route(query) == "OUT_OF_SCOPE", f"Failed on OOS query: {query}"

def test_safety_refuser():
    refuser = SafetyRefuser()
    
    advisory_refusal = refuser.get_refusal("ADVISORY")
    assert "cannot provide investment advice" in advisory_refusal
    assert refuser.educational_url is None
    
    comparative_refusal = refuser.get_refusal("COMPARATIVE")
    assert "cannot compare" in comparative_refusal
    assert refuser.educational_url is None
    
    oos_refusal = refuser.get_refusal("OUT_OF_SCOPE")
    assert "outside the scope" in oos_refusal
    assert refuser.educational_url is None
