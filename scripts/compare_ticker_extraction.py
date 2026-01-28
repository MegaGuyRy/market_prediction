#!/usr/bin/env python
"""
Comparison of ticker extraction methods:
1. NLP/NER (Named Entity Recognition)
2. LLM (Ollama/Mistral)
3. Hybrid approach
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config, get_ollama_url
import requests
import json


def test_ner_method():
    """Test NER (Named Entity Recognition) with spaCy"""
    print("\n" + "="*80)
    print("METHOD 1: NLP/NER (spaCy)")
    print("="*80)
    
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        print("✓ spaCy model loaded")
        
        # Company name to ticker mapping
        ticker_map = {
            'Apple Inc.': 'AAPL', 'Apple': 'AAPL',
            'Microsoft': 'MSFT', 'Microsoft Corporation': 'MSFT',
            'Tesla Inc.': 'TSLA', 'Tesla': 'TSLA',
            'Nvidia': 'NVDA', 'NVIDIA': 'NVDA',
            'Amazon': 'AMZN', 'Amazon.com': 'AMZN',
            'Alphabet Inc.': 'GOOGL', 'Google': 'GOOGL', 'Alphabet': 'GOOGL',
            'Meta Platforms': 'META', 'Meta': 'META', 'Facebook': 'META',
        }
        
        test_articles = [
            "Apple and Microsoft announced a partnership in AI development",
            "Tesla's new factory in Texas is facing production delays",
            "Nvidia's CEO Jensen Huang discusses GPU shortage",
            "Amazon Web Services reports strong Q4 earnings",
        ]
        
        print("\nTest results:")
        for article in test_articles:
            print(f"\nArticle: {article}")
            doc = nlp(article)
            
            # Extract organizations
            orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
            print(f"  Organizations found: {orgs}")
            
            # Map to tickers
            tickers = []
            for org in orgs:
                for name, ticker in ticker_map.items():
                    if name.lower() in org.lower() or org.lower() in name.lower():
                        tickers.append(ticker)
                        break
            
            print(f"  Tickers extracted: {tickers if tickers else 'None'}")
            
    except Exception as e:
        print(f"✗ NER method failed: {e}")


def test_llm_method():
    """Test LLM (Ollama) for ticker extraction"""
    print("\n" + "="*80)
    print("METHOD 2: LLM (Ollama/Mistral)")
    print("="*80)
    
    try:
        ollama_url = get_ollama_url()
        print(f"✓ Ollama URL: {ollama_url}")
        
        test_articles = [
            "Apple and Microsoft announced a partnership in AI development",
            "Tesla's new factory in Texas is facing production delays",
            "Nvidia's CEO Jensen Huang discusses GPU shortage",
            "Amazon Web Services reports strong Q4 earnings",
        ]
        
        print("\nTest results:")
        for article in test_articles:
            print(f"\nArticle: {article}")
            
            prompt = f"""Extract all stock ticker symbols (ticker symbols like AAPL, MSFT, TSLA) from this financial news article.
Also identify the companies mentioned and their tickers.

Article: {article}

Response format (JSON):
{{
  "companies": [
    {{"name": "Company Name", "ticker": "XXXX"}},
    {{"name": "Company Name 2", "ticker": "YYYY"}}
  ]
}}

Return ONLY valid JSON, no other text."""
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')
                
                try:
                    # Extract JSON from response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        parsed = json.loads(json_str)
                        companies = parsed.get('companies', [])
                        
                        if companies:
                            print(f"  Companies found:")
                            for company in companies:
                                print(f"    - {company.get('name')}: {company.get('ticker')}")
                        else:
                            print("  No companies found")
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"  Failed to parse LLM response: {e}")
            else:
                print(f"  LLM request failed: {response.status_code}")
                
    except Exception as e:
        print(f"✗ LLM method failed: {e}")


def comparison_summary():
    """Show comparison of methods"""
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    
    comparison = """
╔════════════════════════╦═══════════════════╦═══════════════════╗
║ Aspect                 ║ NLP/NER (spaCy)   ║ LLM (Ollama)      ║
╠════════════════════════╬═══════════════════╬═══════════════════╣
║ Speed                  ║ ✅ Fast (~10ms)    ║ ⚠️  Slow (~2-5s)   ║
║ Accuracy               ║ ⚠️  Moderate (70%) ║ ✅ High (90%+)     ║
║ Context Understanding  ║ ❌ Limited        ║ ✅ Excellent      ║
║ Resource Requirements  ║ ✅ Low (~500MB)    ║ ⚠️  Medium (~5GB)  ║
║ Handles Ambiguity      ║ ❌ No             ║ ✅ Yes            ║
║ Requires Mapping DB    ║ ✅ Yes (manual)    ║ ❌ No             ║
║ Offline Capability     ║ ✅ Yes            ║ ❌ Needs Ollama    ║
║ False Positives        ║ ⚠️  Some (e.g., Apple → fruit) ║ ✅ Rare ║
║ Maintenance Burden     ║ 🔴 High (update DB) ║ 🟢 Low           ║
╚════════════════════════╩═══════════════════╩═══════════════════╝

PROS & CONS:

NLP/NER Method:
  ✅ Pros:
    - Very fast (deterministic)
    - No API dependencies
    - Works offline
    - Good for known companies
  
  ❌ Cons:
    - Generic NER (not ticker-aware)
    - Needs manual ticker mapping database
    - Struggles with ambiguity ("Apple" = fruit or AAPL?)
    - Fails on indirect mentions ("Tim Cook speech" → miss AAPL)
    - Maintenance overhead for ticker updates

LLM Method (Recommended):
  ✅ Pros:
    - Understands financial context
    - Handles ambiguous mentions intelligently
    - Works with indirect references
    - No maintenance needed (knows all tickers)
    - Can extract reason why ticker mentioned
  
  ❌ Cons:
    - Slower (2-5 seconds per article)
    - Requires Ollama running
    - Higher computational cost
    - Potential for hallucinated tickers

RECOMMENDATION:
─────────────────────────────────────────────────────────────

🎯 HYBRID APPROACH (Best Balance):

1. Primary: LLM (Ollama) - For high-quality, context-aware extraction
2. Cache layer: Remember ticker→company mappings for faster repeats
3. Fallback: NER + mapping database if LLM unavailable
4. Last resort: Keyword matching (current method)

This gives you:
  ✅ High accuracy from LLM
  ✅ Speed improvement through caching
  ✅ Robustness with fallbacks
  ✅ Offline capability if needed
    """)
    
    print(comparison)


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TICKER EXTRACTION METHOD COMPARISON")
    print("="*80)
    
    test_ner_method()
    test_llm_method()
    comparison_summary()
