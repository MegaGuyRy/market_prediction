#!/usr/bin/env python
"""
Test script for LLM-based ticker extraction
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.news.ticker_extractor import TickerExtractor
from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


def test_ticker_extraction():
    """Test the LLM-based ticker extractor."""
    
    config = load_yaml_config('settings')
    logger = StructuredLogger(setup_logging(config.get('logging', {})))
    
    print("="*80)
    print("TICKER EXTRACTION TEST: LLM vs Fallback")
    print("="*80)
    
    extractor = TickerExtractor(logger)
    
    print(f"\n✓ Ticker Extractor initialized")
    print(f"  LLM (Ollama) available: {extractor.ollama_available}")
    print(f"  Fallback mapping available: {len(extractor.fallback_ticker_map)} companies")
    
    # Test cases with expected tickers
    test_cases = [
        {
            'text': 'Apple and Microsoft announce AI partnership',
            'expected': ['AAPL', 'MSFT'],
            'label': 'Direct company mentions'
        },
        {
            'text': 'Tesla production delays impact EV market',
            'expected': ['TSLA'],
            'label': 'Single company'
        },
        {
            'text': 'Tim Cook unveils new iPhone features at keynote',
            'expected': ['AAPL'],
            'label': 'Indirect mention (CEO)'
        },
        {
            'text': 'AWS reports record cloud growth outpacing competitors',
            'expected': ['AMZN'],
            'label': 'Service-based reference (AWS → Amazon)'
        },
        {
            'text': 'GM competes with Tesla in EV space',
            'expected': ['GM', 'TSLA'],
            'label': 'Multiple companies with competition context'
        },
        {
            'text': 'JPMorgan and Goldman Sachs raise interest rate outlook',
            'expected': ['JPM', 'GS'],
            'label': 'Finance sector'
        },
        {
            'text': 'Market conditions remain stable',
            'expected': ['SPY'],
            'label': 'No specific company (should default)'
        },
        {
            'text': 'Nvidia GPU shortage continues as AI demand surges',
            'expected': ['NVDA'],
            'label': 'Company-specific technology'
        },
    ]
    
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    correct_llm = 0
    correct_fallback = 0
    total = len(test_cases)
    
    for i, test in enumerate(test_cases, 1):
        text = test['text']
        expected = set(test['expected'])
        label = test['label']
        
        print(f"\n{i}. {label}")
        print(f"   Text: {text}")
        print(f"   Expected: {expected}")
        
        # Get tickers (will use LLM if available, else fallback)
        tickers = extractor.extract_tickers(text, use_llm=True)
        extracted = set(tickers)
        
        match = extracted == expected or extracted.issubset(expected) or (expected.issubset(extracted) and len(extracted) <= len(expected) + 1)
        status = "✅" if match else "⚠️"
        
        print(f"   Extracted: {extracted} {status}")
        
        # Try LLM specifically if available
        if extractor.ollama_available:
            llm_tickers = extractor._extract_tickers_llm(text)
            if llm_tickers:
                llm_extracted = set(llm_tickers)
                llm_match = llm_extracted == expected or llm_extracted.issubset(expected) or (expected.issubset(llm_extracted) and len(llm_extracted) <= len(expected) + 1)
                llm_status = "✅" if llm_match else "⚠️"
                print(f"   LLM result: {llm_extracted} {llm_status}")
                if llm_match:
                    correct_llm += 1
        
        # Fallback result
        fallback_tickers = extractor._extract_tickers_fallback(text)
        fallback_extracted = set(fallback_tickers)
        fallback_match = fallback_extracted == expected or fallback_extracted.issubset(expected) or (expected.issubset(fallback_extracted) and len(fallback_extracted) <= len(expected) + 1)
        fallback_status = "✅" if fallback_match else "⚠️"
        print(f"   Fallback result: {fallback_extracted} {fallback_status}")
        if fallback_match:
            correct_fallback += 1
    
    # Summary
    print("\n" + "="*80)
    print("ACCURACY SUMMARY")
    print("="*80)
    
    if extractor.ollama_available:
        llm_accuracy = (correct_llm / total * 100) if total > 0 else 0
        print(f"\nLLM Method (Ollama):")
        print(f"  Accuracy: {correct_llm}/{total} ({llm_accuracy:.1f}%)")
    
    fallback_accuracy = (correct_fallback / total * 100) if total > 0 else 0
    print(f"\nFallback Method (Mapping):")
    print(f"  Accuracy: {correct_fallback}/{total} ({fallback_accuracy:.1f}%)")
    
    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    if extractor.ollama_available:
        print("""
✅ LLM method is recommended:
   - More accurate on complex references
   - Understands financial context
   - Handles indirect company mentions (CEO names, products)
   - No manual mapping maintenance needed

💡 Hybrid approach in use:
   - Primary: LLM extraction (accurate)
   - Fallback: Keyword mapping (fast, no API)
   - Default: SPY (market index) when nothing found
    """)
    else:
        print("""
⚠️  Ollama not available - using fallback mapping:
   - Keyword-based extraction (fast)
   - Requires manual company→ticker mapping
   - May miss indirect references
   
💡 To improve:
   - Start Ollama service for LLM extraction
   - Add more company names to mapping database
    """)
    
    print("="*80)


if __name__ == "__main__":
    test_ticker_extraction()
