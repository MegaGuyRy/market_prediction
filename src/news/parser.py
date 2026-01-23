"""
News Parser Module
Extract sentiment and novelty scores from news items.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any
import numpy as np
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import get_database_url, load_yaml_config, get_ollama_url
from utils.logging import StructuredLogger, setup_logging


class NewsParser:
    """Parse news items for sentiment and novelty."""
    
    def __init__(self, logger: StructuredLogger = None, use_ollama: bool = True):
        """
        Initialize news parser.
        
        Args:
            logger: StructuredLogger instance
            use_ollama: Whether to use Ollama for sentiment (else simple heuristics)
        """
        self.config = load_yaml_config('settings')
        self.logger = logger or StructuredLogger(setup_logging(self.config.get('logging', {})))
        
        self.use_ollama = use_ollama
        if self.use_ollama:
            try:
                import requests
                self.ollama_url = get_ollama_url()
                self.requests = requests
                self.logger.info("News parser initialized with Ollama", url=self.ollama_url)
            except Exception as e:
                self.logger.warning(f"Ollama not available, using heuristics: {e}")
                self.use_ollama = False
    
    def extract_sentiment(self, text: str, use_llm: bool = None) -> float:
        """
        Extract sentiment score from text.
        
        Args:
            text: Text to analyze
            use_llm: Override use_ollama setting for this call
        
        Returns:
            Sentiment score from -1 (very bearish) to +1 (very bullish)
        """
        try:
            if use_llm is None:
                use_llm = self.use_ollama
            
            if use_llm:
                return self._extract_sentiment_ollama(text)
            else:
                return self._extract_sentiment_heuristic(text)
                
        except Exception as e:
            self.logger.warning(f"Failed to extract sentiment: {e}")
            return 0.0
    
    def _extract_sentiment_ollama(self, text: str) -> float:
        """Extract sentiment using Ollama LLM."""
        try:
            # Truncate text to avoid token limits
            text_preview = text[:1000]
            
            prompt = f"""Analyze the sentiment of this financial news. 
Return ONLY a JSON object with "sentiment" score from -1 (very bearish) to +1 (very bullish).

News: {text_preview}

Response format: {{"sentiment": <float>}}"""
            
            response = self.requests.post(
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
                    # Extract JSON object from response
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = response_text[json_start:json_end]
                        parsed = json.loads(json_str)
                        sentiment = float(parsed.get('sentiment', 0))
                        # Clamp to [-1, 1]
                        sentiment = max(-1, min(1, sentiment))
                        return sentiment
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # Fallback to heuristic if LLM fails
            return self._extract_sentiment_heuristic(text)
            
        except Exception as e:
            self.logger.debug(f"Ollama sentiment extraction failed: {e}")
            return self._extract_sentiment_heuristic(text)
    
    def _extract_sentiment_heuristic(self, text: str) -> float:
        """Extract sentiment using keyword heuristics."""
        text_lower = text.lower()
        
        # Bullish indicators
        bullish_keywords = [
            'beat earnings', 'upbeat', 'surge', 'rally', 'gain', 'strong',
            'upgrade', 'bullish', 'jump', 'soar', 'breakthrough', 'deal',
            'partnership', 'merger', 'record', 'profit', 'outperform',
            'beat', 'top analyst', 'buy', 'outflow reduction'
        ]
        
        # Bearish indicators
        bearish_keywords = [
            'miss earnings', 'downgrade', 'downbeat', 'decline', 'loss',
            'weak', 'bearish', 'crash', 'plunge', 'sell', 'lawsuit',
            'scandal', 'recall', 'investigation', 'warning', 'delay',
            'underperform', 'cut', 'outflow', 'regulatory'
        ]
        
        bullish_score = sum(1 for keyword in bullish_keywords 
                           if keyword in text_lower)
        bearish_score = sum(1 for keyword in bearish_keywords 
                           if keyword in text_lower)
        
        # Calculate sentiment (-1 to 1)
        total = bullish_score + bearish_score
        if total == 0:
            return 0.0
        
        sentiment = (bullish_score - bearish_score) / (total * 0.5)
        return max(-1, min(1, sentiment))
    
    def score_novelty(self, headline: str, embedding: np.ndarray,
                     existing_embeddings: List[np.ndarray] = None,
                     similarity_threshold: float = 0.85) -> float:
        """
        Score novelty of a news item.
        
        Args:
            headline: News headline
            embedding: Vector embedding of the news
            existing_embeddings: List of existing news embeddings to compare against
            similarity_threshold: Threshold above which items are considered duplicates
        
        Returns:
            Novelty score from 0 (duplicate) to 1 (novel)
        """
        try:
            # If no existing embeddings, assume novel
            if not existing_embeddings:
                return 1.0
            
            # Calculate similarity to most similar existing news
            embeddings_array = np.array(existing_embeddings)
            
            # Normalize for cosine similarity
            embedding_norm = embedding / (np.linalg.norm(embedding) + 1e-10)
            embeddings_norm = embeddings_array / (
                np.linalg.norm(embeddings_array, axis=1, keepdims=True) + 1e-10
            )
            
            # Calculate cosine similarity
            similarities = np.dot(embeddings_norm, embedding_norm)
            max_similarity = np.max(similarities)
            
            # Convert similarity to novelty (inverse relationship)
            # High similarity = low novelty, low similarity = high novelty
            novelty = max(0, 1 - max_similarity)
            
            return float(novelty)
            
        except Exception as e:
            self.logger.warning(f"Failed to score novelty: {e}")
            return 0.5  # Neutral novelty on error
    
    def parse_news_item(self, news_item: Dict[str, Any],
                       existing_embeddings: List[np.ndarray] = None) -> Dict[str, Any]:
        """
        Parse a single news item with sentiment and novelty scores.
        
        Args:
            news_item: Dict with keys: headline, content, embedding, source, url, published_at
            existing_embeddings: For novelty scoring
        
        Returns:
            Enriched dict with sentiment_score and novelty_score
        """
        try:
            # Extract sentiment
            combined_text = f"{news_item.get('headline', '')} {news_item.get('content', '')}"
            sentiment = self.extract_sentiment(combined_text)
            
            # Score novelty
            embedding = news_item.get('embedding')
            novelty = self.score_novelty(
                news_item.get('headline', ''),
                embedding,
                existing_embeddings
            )
            
            # Add scores to item
            news_item['sentiment_score'] = float(sentiment)
            news_item['novelty_score'] = float(novelty)
            
            self.logger.debug(f"Parsed news item",
                            headline=news_item['headline'][:50],
                            sentiment=round(sentiment, 2),
                            novelty=round(novelty, 2))
            
            return news_item
            
        except Exception as e:
            self.logger.error(f"Failed to parse news item: {e}")
            news_item['sentiment_score'] = 0.0
            news_item['novelty_score'] = 0.5
            return news_item
    
    def batch_parse_news(self, news_items: List[Dict[str, Any]],
                        existing_embeddings: List[np.ndarray] = None) -> List[Dict[str, Any]]:
        """
        Parse multiple news items.
        
        Args:
            news_items: List of news items to parse
            existing_embeddings: For novelty scoring
        
        Returns:
            List of parsed news items with sentiment and novelty scores
        """
        parsed_items = []
        for item in news_items:
            parsed = self.parse_news_item(item, existing_embeddings)
            parsed_items.append(parsed)
        
        self.logger.info(f"Batch parsed {len(parsed_items)} news items",
                        count=len(parsed_items))
        return parsed_items


def extract_sentiment(text: str) -> float:
    """Convenience function to extract sentiment."""
    parser = NewsParser()
    return parser.extract_sentiment(text)


def score_novelty(headline: str, embedding: np.ndarray,
                 existing_embeddings: List[np.ndarray] = None) -> float:
    """Convenience function to score novelty."""
    parser = NewsParser()
    return parser.score_novelty(headline, embedding, existing_embeddings)


if __name__ == "__main__":
    # Test script
    print("="*60)
    print("NEWS PARSER TEST")
    print("="*60)
    
    # Initialize parser (use heuristics to avoid Ollama dependency)
    parser = NewsParser(use_ollama=True)
    
    # Test sentiment extraction
    print("\n1. SENTIMENT EXTRACTION TEST")
    print("-"*60)
    
    test_cases = [
        ("Apple beats earnings with record iPhone sales", "Expected: Positive"),
        ("Tesla stock crashes after missing delivery targets", "Expected: Negative"),
        ("Microsoft announces partnership with OpenAI", "Expected: Positive"),
        ("Company faces lawsuit over regulatory violations", "Expected: Negative"),
        ("Stock price remains unchanged", "Expected: Neutral"),
    ]
    
    for text, expected in test_cases:
        sentiment = parser.extract_sentiment(text, use_llm=False)
        emoji = "📈" if sentiment > 0.2 else "📉" if sentiment < -0.2 else "➡️"
        print(f"{emoji} {sentiment:+.2f} | {text}")
        print(f"   {expected}")
    
    # Test novelty scoring with embeddings
    print("\n2. NOVELTY SCORING TEST")
    print("-"*60)
    
    from embedder import NewsEmbedder
    embedder = NewsEmbedder()
    
    # Create some existing news embeddings (simulate historical news)
    existing_headlines = [
        "Apple releases new iPhone with better camera",
        "Apple announces iPhone 15 with improved battery",
    ]
    existing_embeddings = [embedder.embed_text(h) for h in existing_headlines]
    
    # Test novelty of new headlines
    test_novelty = [
        ("Apple unveils iPhone 16 with enhanced features", "Similar to existing"),
        ("Tesla announces new Cybertruck production milestone", "Different topic"),
        ("Apple iPhone gets minor software update", "Very similar"),
    ]
    
    for headline, note in test_novelty:
        embedding = embedder.embed_text(headline)
        novelty = parser.score_novelty(headline, embedding, existing_embeddings)
        emoji = "🆕" if novelty > 0.7 else "🔄" if novelty > 0.4 else "📰"
        print(f"{emoji} Novelty: {novelty:.2f} | {headline}")
        print(f"   {note}")
    
    # Test full news item parsing
    print("\n3. FULL NEWS ITEM PARSING")
    print("-"*60)
    
    news_items = [
        {
            "headline": "Apple beats Q4 earnings expectations",
            "content": "Apple Inc reported strong earnings with record iPhone sales.",
            "source": "Financial Times",
            "url": "https://example.com/apple-earnings",
        },
        {
            "headline": "Tech stocks plunge on regulatory concerns",
            "content": "Major tech companies face new regulatory scrutiny.",
            "source": "Reuters",
            "url": "https://example.com/tech-regulation",
        }
    ]
    
    # Add embeddings to items
    from embedder import NewsEmbedder
    embedder = NewsEmbedder()
    for item in news_items:
        combined = f"{item['headline']} {item['content']}"
        item['embedding'] = embedder.embed_text(combined)
    
    # Parse items
    parsed_items = parser.batch_parse_news(news_items, existing_embeddings)
    
    for item in parsed_items:
        print(f"\nHeadline: {item['headline']}")
        print(f"Source: {item['source']}")
        sentiment_label = "Bullish" if item['sentiment_score'] > 0.2 else "Bearish" if item['sentiment_score'] < -0.2 else "Neutral"
        novelty_label = "Novel" if item['novelty_score'] > 0.7 else "Familiar" if item['novelty_score'] < 0.4 else "Moderate"
        print(f"Sentiment: {item['sentiment_score']:+.2f} ({sentiment_label})")
        print(f"Novelty: {item['novelty_score']:.2f} ({novelty_label})")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
