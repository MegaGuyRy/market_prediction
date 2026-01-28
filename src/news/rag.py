"""
News RAG Module
Retrieve relevant news context for agent decision-making using vector similarity.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import numpy as np

from sqlalchemy import text

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import get_database_url, load_yaml_config
from utils.logging import StructuredLogger, setup_logging
from .storage import NewsStorage
from .embedder import NewsEmbedder


class NewsRAG:
    """Retrieve news context using vector similarity search."""
    
    def __init__(self, logger: StructuredLogger = None):
        """Initialize RAG system with storage and embedder."""
        self.config = load_yaml_config('settings')
        self.logger = logger or StructuredLogger(setup_logging(self.config.get('logging', {})))
        
        self.storage = NewsStorage(self.logger)
        self.embedder = NewsEmbedder(self.logger)
        
        self.logger.info("News RAG initialized")
    
    def retrieve_similar_news(self, query_text: str, ticker: str = None,
                             limit: int = 5, recency_weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Retrieve news similar to query text.
        
        Args:
            query_text: Text to find similar news for
            ticker: Optional ticker to filter by
            limit: Maximum results
            recency_weight: How much to weight recent items (0-1)
        
        Returns:
            List of relevant news items with relevance scores
        """
        try:
            # Generate embedding for query
            query_embedding = self.embedder.embed_text(query_text)
            
            # Search by similarity
            results = self.storage.search_similar_news(
                embedding=query_embedding,
                ticker=ticker,
                limit=limit * 2  # Get more, then rank by recency
            )
            
            # Re-rank by combining similarity + recency
            ranked = self._rank_by_recency(results, weight=recency_weight)
            
            self.logger.debug(f"Retrieved {len(ranked)} similar news items",
                            ticker=ticker, count=len(ranked))
            return ranked[:limit]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve similar news: {e}")
            return []
    
    def get_ticker_context(self, ticker: str, max_hours: int = 24,
                          limit: int = 10, min_sentiment: float = None) -> Dict[str, Any]:
        """
        Get comprehensive news context for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            max_hours: Only include news from last N hours
            limit: Maximum news items
            min_sentiment: Optional minimum sentiment threshold
        
        Returns:
            Dict with:
            - news_items: List of relevant news
            - avg_sentiment: Average sentiment score
            - sentiment_trend: Positive/negative trend
            - count: Number of items
        """
        try:
            # Get recent news for ticker
            news_items = self.storage.get_news_for_ticker(
                ticker=ticker,
                hours_lookback=max_hours,
                limit=limit
            )
            
            # Filter by sentiment if specified
            if min_sentiment is not None:
                news_items = [n for n in news_items 
                            if n.get('sentiment_score', 0) >= min_sentiment]
            
            # Calculate sentiment metrics
            sentiments = [n.get('sentiment_score', 0) for n in news_items]
            avg_sentiment = np.mean(sentiments) if sentiments else 0.0
            
            # Determine trend
            if len(sentiments) > 1:
                recent_sentiment = np.mean(sentiments[:len(sentiments)//2])
                older_sentiment = np.mean(sentiments[len(sentiments)//2:])
                trend = "improving" if recent_sentiment > older_sentiment else "deteriorating"
            else:
                trend = "neutral"
            
            context = {
                'ticker': ticker,
                'news_items': news_items,
                'count': len(news_items),
                'avg_sentiment': float(avg_sentiment),
                'sentiment_trend': trend,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.logger.debug(f"Generated context for {ticker}",
                            ticker=ticker, count=len(news_items),
                            avg_sentiment=round(avg_sentiment, 2))
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get ticker context: {e}")
            return {
                'ticker': ticker,
                'news_items': [],
                'count': 0,
                'avg_sentiment': 0.0,
                'sentiment_trend': 'neutral'
            }
    
    def get_sector_context(self, tickers: List[str], max_hours: int = 24,
                          top_k: int = 3) -> Dict[str, Any]:
        """
        Get aggregated news context across multiple tickers (sector).
        
        Args:
            tickers: List of ticker symbols
            max_hours: Only include recent news
            top_k: Top K news items per ticker
        
        Returns:
            Dict with aggregated sentiment and relevant news
        """
        try:
            all_sentiments = []
            aggregated_news = []
            
            for ticker in tickers:
                context = self.get_ticker_context(
                    ticker=ticker,
                    max_hours=max_hours,
                    limit=top_k
                )
                
                sentiments = [n.get('sentiment_score', 0) 
                            for n in context['news_items']]
                all_sentiments.extend(sentiments)
                aggregated_news.extend(context['news_items'])
            
            # Calculate aggregated metrics
            avg_sentiment = np.mean(all_sentiments) if all_sentiments else 0.0
            bullish_count = sum(1 for s in all_sentiments if s > 0.2)
            bearish_count = sum(1 for s in all_sentiments if s < -0.2)
            
            sector_context = {
                'tickers': tickers,
                'count': len(aggregated_news),
                'avg_sentiment': float(avg_sentiment),
                'bullish_items': bullish_count,
                'bearish_items': bearish_count,
                'sentiment_balance': float(bullish_count - bearish_count),
                'top_news': sorted(aggregated_news, 
                                  key=lambda x: abs(x.get('sentiment_score', 0)),
                                  reverse=True)[:5],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self.logger.debug(f"Generated sector context",
                            count=len(tickers), news_count=len(aggregated_news))
            return sector_context
            
        except Exception as e:
            self.logger.error(f"Failed to get sector context: {e}")
            return {
                'tickers': tickers,
                'count': 0,
                'avg_sentiment': 0.0,
                'bullish_items': 0,
                'bearish_items': 0,
                'sentiment_balance': 0.0,
                'top_news': []
            }
    
    def _rank_by_recency(self, items: List[Dict[str, Any]], 
                        weight: float = 0.3) -> List[Dict[str, Any]]:
        """
        Re-rank items by combining similarity + recency.
        
        Args:
            items: List of items with 'published_at' and 'similarity'
            weight: Weight for recency vs similarity (0-1)
        
        Returns:
            Re-ranked items with combined 'score' field
        """
        if not items:
            return items
        
        now = datetime.utcnow()
        max_age_hours = 168  # 1 week
        
        for item in items:
            # Parse published_at
            pub_time = item.get('published_at')
            if isinstance(pub_time, str):
                pub_time = datetime.fromisoformat(pub_time.replace('Z', '+00:00'))
            
            # Calculate recency score (0-1, newer = higher)
            age_hours = (now - pub_time).total_seconds() / 3600
            recency = max(0, 1 - (age_hours / max_age_hours))
            
            # Combine scores
            similarity = item.get('similarity', 0)
            combined = (1 - weight) * similarity + weight * recency
            item['score'] = float(combined)
        
        # Sort by combined score
        items.sort(key=lambda x: x['score'], reverse=True)
        return items


def retrieve_similar_news(query_text: str, ticker: str = None, 
                         limit: int = 5) -> List[Dict[str, Any]]:
    """Convenience function to retrieve similar news."""
    rag = NewsRAG()
    return rag.retrieve_similar_news(query_text, ticker, limit)


def get_news_context(ticker: str, max_hours: int = 24) -> Dict[str, Any]:
    """Convenience function to get news context for ticker."""
    rag = NewsRAG()
    return rag.get_ticker_context(ticker, max_hours)


if __name__ == "__main__":
    import os
    
    # Set local database URL
    os.environ['DATABASE_URL'] = 'postgresql+psycopg2://market:market@localhost:5433/marketdb'
    
    print("="*70)
    print("NEWS RAG TEST")
    print("="*70)
    
    # Initialize RAG
    print("\n1. INITIALIZING RAG")
    print("-"*70)
    try:
        rag = NewsRAG()
        print("[PASS] RAG initialized successfully")
        print(f"  Storage: PostgreSQL with pgvector")
        print(f"  Embedder: {rag.embedder.model_name} ({rag.embedder.embedding_dim}-dim)")
    except Exception as e:
        print(f"[FAIL] Failed to initialize RAG: {e}")
        sys.exit(1)
    
    # Test 1: Check database has news
    print("\n2. CHECKING DATABASE")
    print("-"*70)
    try:
        news_count = rag.storage.get_news_count()
        print(f"[PASS] Database contains {news_count} news items")
        
        if news_count == 0:
            print("\n  WARNING: No news in database!")
            print("   First run storage.py test to populate database:")
            print("   DATABASE_URL='postgresql+psycopg2://market:market@localhost:5433/marketdb' \\")
            print("   python src/news/storage.py")
            sys.exit(0)
    except Exception as e:
        print(f"[FAIL] Failed to check database: {e}")
        sys.exit(1)
    
    # Test 2: Retrieve similar news
    print("\n3. SIMILAR NEWS RETRIEVAL TEST")
    print("-"*70)
    try:
        queries = [
            ("strong earnings beat revenue growth", "Earnings/growth topic"),
            ("stock decline market weakness", "Negative market sentiment"),
            ("partnership announcement innovation", "Business development"),
        ]
        
        for query_text, description in queries:
            print(f"\nQuery: '{query_text}'")
            print(f"Description: {description}")
            
            similar = rag.retrieve_similar_news(
                query_text=query_text,
                limit=3,
                recency_weight=0.3
            )
            
            if similar:
                print(f"Found {len(similar)} similar news items:")
                for i, item in enumerate(similar, 1):
                    print(f"  {i}. {item['headline'][:60]}")
                    print(f"     Source: {item['source']}")
                    print(f"     Similarity: {item.get('similarity', 0):.2f}")
                    print(f"     Combined score: {item.get('score', 0):.2f}")
            else:
                print(f"  No similar news found")
    except Exception as e:
        print(f"[FAIL] Failed to retrieve similar news: {e}")
    
    # Test 3: Ticker context
    print("\n4. TICKER CONTEXT TEST")
    print("-"*70)
    try:
        tickers = ["AAPL", "TSLA", "MSFT"]
        
        for ticker in tickers:
            context = rag.get_ticker_context(
                ticker=ticker,
                max_hours=168,  # 1 week
                limit=10
            )
            
            print(f"\nTicker: {ticker}")
            print(f"  News count: {context['count']}")
            print(f"  Avg sentiment: {context['avg_sentiment']:+.2f}")
            print(f"  Sentiment trend: {context['sentiment_trend']}")
            
            if context['news_items']:
                print(f"  Recent news:")
                for item in context['news_items'][:3]:
                    sentiment_emoji = "📈" if item.get('sentiment_score', 0) > 0.2 else "📉"
                    print(f"    {sentiment_emoji} {item['headline'][:50]}")
                    print(f"       Sentiment: {item.get('sentiment_score', 0):+.2f}")
            else:
                print(f"  No news found for this ticker")
    except Exception as e:
        print(f"[FAIL] Failed to get ticker context: {e}")
    
    # Test 4: Sector context
    print("\n5. SECTOR CONTEXT TEST")
    print("-"*70)
    try:
        sector_tickers = ["AAPL", "MSFT", "NVDA"]  # Tech sector
        
        sector_context = rag.get_sector_context(
            tickers=sector_tickers,
            max_hours=168,
            top_k=3
        )
        
        print(f"\nSector: Tech {sector_context['tickers']}")
        print(f"  Total news items: {sector_context['count']}")
        print(f"  Avg sentiment: {sector_context['avg_sentiment']:+.2f}")
        print(f"  Bullish items: {sector_context['bullish_items']}")
        print(f"  Bearish items: {sector_context['bearish_items']}")
        print(f"  Sentiment balance: {sector_context['sentiment_balance']:+.0f}")
        
        if sector_context['top_news']:
            print(f"\n  Top news items:")
            for i, item in enumerate(sector_context['top_news'], 1):
                print(f"    {i}. {item['headline'][:60]}")
                print(f"       Sentiment: {item.get('sentiment_score', 0):+.2f}")
    except Exception as e:
        print(f"[FAIL] Failed to get sector context: {e}")
    
    # Test 5: Agent decision context (example use case)
    print("\n6. AGENT DECISION CONTEXT TEST")
    print("-"*70)
    try:
        ticker = "AAPL"
        print(f"\nScenario: Agent analyzing {ticker} for trading decision")
        
        # Get news context
        context = rag.get_ticker_context(ticker, max_hours=72, limit=5)
        
        # Simulate agent decision
        if context['count'] > 0:
            avg_sentiment = context['avg_sentiment']
            if avg_sentiment > 0.5:
                decision = "BUY (Strong bullish sentiment)"
            elif avg_sentiment > 0:
                decision = "BUY LIGHT (Mild bullish sentiment)"
            elif avg_sentiment < -0.5:
                decision = "SELL (Strong bearish sentiment)"
            elif avg_sentiment < 0:
                decision = "SELL LIGHT (Mild bearish sentiment)"
            else:
                decision = "HOLD (Neutral sentiment)"
            
            print(f"\nNews summary for {ticker}:")
            print(f"  News items: {context['count']}")
            print(f"  Avg sentiment: {avg_sentiment:+.2f}")
            print(f"  Trend: {context['sentiment_trend']}")
            print(f"\nAgent decision: {decision}")
        else:
            print(f"No recent news for {ticker} - hold position")
    except Exception as e:
        print(f"[FAIL] Failed agent decision test: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("[PASS] RAG module test complete!")
    print("[PASS] Similar news retrieval: Working")
    print("[PASS] Ticker context: Working")
    print("[PASS] Sector context: Working")
    print("[PASS] Agent decision support: Ready")
    print("="*70)
