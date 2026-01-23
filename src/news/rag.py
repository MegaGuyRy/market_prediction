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
