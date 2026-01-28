"""
Ticker Extraction Module
Extracts stock ticker symbols from financial news using LLM with caching and fallbacks.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import requests
from functools import lru_cache

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import get_ollama_url
from utils.logging import StructuredLogger, setup_logging
from utils.config import load_yaml_config


class TickerExtractor:
    """Extract stock tickers from news using LLM with intelligent fallbacks."""
    
    def __init__(self, logger: StructuredLogger = None):
        """
        Initialize ticker extractor.
        
        Args:
            logger: StructuredLogger instance
        """
        self.config = load_yaml_config('settings')
        self.logger = logger or StructuredLogger(setup_logging(self.config.get('logging', {})))
        
        # Initialize Ollama if available
        self.ollama_available = False
        try:
            self.ollama_url = get_ollama_url()
            # Test connection
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=2)
            if response.status_code == 200:
                self.ollama_available = True
                self.logger.info("Ollama LLM available for ticker extraction", url=self.ollama_url)
        except Exception as e:
            self.logger.warning(f"Ollama not available for ticker extraction: {e}")
        
        # Fallback company->ticker mapping (for when LLM unavailable)
        self.fallback_ticker_map = {
            # Tech Giants
            'apple': 'AAPL', 'apple inc': 'AAPL', 'apple inc.': 'AAPL',
            'microsoft': 'MSFT', 'microsoft corporation': 'MSFT',
            'google': 'GOOGL', 'alphabet': 'GOOGL', 'alphabet inc': 'GOOGL',
            'amazon': 'AMZN', 'amazon.com': 'AMZN', 'aws': 'AMZN',
            'meta': 'META', 'facebook': 'META', 'meta platforms': 'META',
            'nvidia': 'NVDA', 'nvidia corporation': 'NVDA',
            
            # Auto
            'tesla': 'TSLA', 'tesla inc': 'TSLA',
            'general motors': 'GM', 'gm': 'GM',
            'ford': 'F', 'ford motor': 'F',
            
            # Finance
            'jpmorgan': 'JPM', 'jp morgan': 'JPM', 'jp morgan chase': 'JPM',
            'goldman sachs': 'GS',
            'bank of america': 'BAC', 'bofa': 'BAC',
            
            # Retail
            'walmart': 'WMT',
            'costco': 'COST',
            'target': 'TGT',
            
            # Healthcare
            'pfizer': 'PFE',
            'moderna': 'MRNA',
            'johnson & johnson': 'JNJ', 'j&j': 'JNJ',
            
            # Energy
            'exxon mobil': 'XOM',
            'chevron': 'CVX',
        }
    
    def extract_tickers(self, text: str, use_llm: bool = True) -> List[str]:
        """
        Extract ticker symbols from text using intelligent fallback approach.
        
        Priority:
        1. LLM (Ollama) - Most accurate
        2. Fallback mapping - Fast
        
        Args:
            text: News headline and/or content
            use_llm: Whether to try LLM extraction first
        
        Returns:
            List of ticker symbols (e.g., ['AAPL', 'MSFT'])
        """
        try:
            # Try LLM first if available and requested
            if use_llm and self.ollama_available:
                tickers = self._extract_tickers_llm(text)
                if tickers:
                    return tickers
            
            # Fall back to mapping-based extraction
            return self._extract_tickers_fallback(text)
            
        except Exception as e:
            self.logger.warning(f"Error extracting tickers: {e}")
            return []
    
    def _extract_tickers_llm(self, text: str) -> Optional[List[str]]:
        """
        Extract tickers using Ollama/Mistral LLM.
        
        Most accurate method - understands context and indirect references.
        """
        try:
            # Truncate text to avoid token limits
            text_truncated = text[:1000]
            
            prompt = f"""Extract all stock ticker symbols mentioned or implied in this financial news.
Include companies mentioned directly (Apple, Tesla) and indirectly (CEO names, product names that imply companies).

Return ONLY a JSON object with a list of ticker symbols. Use standard US stock tickers.

Examples:
- "Apple announces new iPhone" → {{"tickers": ["AAPL"]}}
- "Tesla vs GM in EV race" → {{"tickers": ["TSLA", "GM"]}}
- "Tim Cook speech" → {{"tickers": ["AAPL"]}}
- "AWS reports growth" → {{"tickers": ["AMZN"]}}

News: {text_truncated}

Response format: {{"tickers": ["TICKER1", "TICKER2"]}}
Return ONLY valid JSON, no other text."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
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
                
                # Parse JSON from response
                try:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        parsed = json.loads(json_str)
                        tickers = parsed.get('tickers', [])
                        
                        if tickers:
                            # Validate tickers (should be 1-5 chars, uppercase)
                            valid_tickers = [
                                t.upper() for t in tickers 
                                if isinstance(t, str) and 1 <= len(t) <= 5 and t.isalpha()
                            ]
                            
                            if valid_tickers:
                                self.logger.debug(
                                    f"LLM extracted tickers",
                                    text_preview=text_truncated[:50],
                                    tickers=valid_tickers
                                )
                                return valid_tickers
                except (json.JSONDecodeError, ValueError, AttributeError):
                    pass
        except requests.Timeout:
            self.logger.debug("LLM request timeout - falling back to mapping")
        except Exception as e:
            self.logger.debug(f"LLM extraction error: {e}")
        
        return None
    
    def _extract_tickers_fallback(self, text: str) -> List[str]:
        """
        Extract tickers using fallback keyword mapping.
        
        Fast but less accurate - relies on company name matching.
        """
        try:
            text_lower = text.lower()
            found_tickers = set()
            
            # Search for company names and map to tickers
            for company_name, ticker in self.fallback_ticker_map.items():
                if company_name in text_lower:
                    found_tickers.add(ticker)
            
            # If no tickers found, default to common major index
            if not found_tickers:
                found_tickers.add('SPY')  # S&P 500 ETF as default
            
            result = list(found_tickers)
            
            if result != ['SPY']:
                self.logger.debug(
                    f"Fallback extracted tickers",
                    text_preview=text[:50],
                    tickers=result
                )
            
            return result
            
        except Exception as e:
            self.logger.warning(f"Fallback ticker extraction error: {e}")
            return ['SPY']  # Default fallback
    
    def extract_tickers_with_reason(self, text: str) -> Dict[str, Any]:
        """
        Extract tickers with reasoning from LLM.
        
        Returns dict with tickers and explanation of why they were mentioned.
        """
        try:
            if not self.ollama_available:
                return {
                    'tickers': self._extract_tickers_fallback(text),
                    'reason': 'Using fallback mapping (LLM unavailable)',
                    'method': 'fallback'
                }
            
            text_truncated = text[:1000]
            
            prompt = f"""Analyze this financial news and extract:
1. All stock ticker symbols mentioned or implied
2. Why each ticker is mentioned

Return JSON format.

News: {text_truncated}

Response format:
{{
  "tickers": [
    {{"ticker": "AAPL", "reason": "Apple announced new earnings"}},
    {{"ticker": "MSFT", "reason": "Competing with Microsoft in cloud"}}
  ]
}}

Return ONLY valid JSON."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.2
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '{}')
                
                try:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        parsed = json.loads(json_str)
                        
                        ticker_data = parsed.get('tickers', [])
                        if ticker_data:
                            tickers = [t.get('ticker', '').upper() for t in ticker_data]
                            reasons = {t.get('ticker', '').upper(): t.get('reason', '') for t in ticker_data}
                            
                            return {
                                'tickers': [t for t in tickers if t],
                                'reasons': reasons,
                                'method': 'llm'
                            }
                except (json.JSONDecodeError, ValueError):
                    pass
        except Exception as e:
            self.logger.debug(f"LLM reasoning extraction failed: {e}")
        
        # Fallback
        tickers = self._extract_tickers_fallback(text)
        return {
            'tickers': tickers,
            'reasons': {t: 'Extracted via fallback mapping' for t in tickers},
            'method': 'fallback'
        }


# Convenience functions
def extract_tickers(text: str, use_llm: bool = True) -> List[str]:
    """Convenience function to extract tickers."""
    extractor = TickerExtractor()
    return extractor.extract_tickers(text, use_llm=use_llm)


if __name__ == "__main__":
    # Test the ticker extractor
    print("="*80)
    print("TICKER EXTRACTOR TEST")
    print("="*80)
    
    config = load_yaml_config('settings')
    logger = StructuredLogger(setup_logging(config.get('logging', {})))
    
    extractor = TickerExtractor(logger)
    
    test_cases = [
        "Apple and Microsoft announce AI partnership",
        "Tesla production delays impact EV market",
        "Tim Cook unveils new iPhone features",
        "AWS reports record cloud growth",
        "GM competes with Tesla in EV space",
        "JPMorgan and Goldman Sachs raise rates",
    ]
    
    print(f"\n✓ Ticker Extractor initialized")
    print(f"  LLM available: {extractor.ollama_available}")
    
    for text in test_cases:
        print(f"\nText: {text}")
        
        # Method 1: Simple extraction
        tickers = extractor.extract_tickers(text)
        print(f"  Tickers: {tickers}")
        
        # Method 2: With reasons
        result = extractor.extract_tickers_with_reason(text)
        print(f"  Method: {result['method']}")
        if result.get('reasons'):
            for ticker, reason in result['reasons'].items():
                print(f"    - {ticker}: {reason}")
