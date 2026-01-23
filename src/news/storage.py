"""
News Storage Module
Store news + embeddings in PostgreSQL with pgvector support.
"""

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import numpy as np

from sqlalchemy import create_engine, text, select, func
from sqlalchemy.orm import Session, sessionmaker
from pgvector.sqlalchemy import Vector

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import get_database_url, load_yaml_config
from utils.logging import StructuredLogger, setup_logging


class NewsStorage:
    """Store and retrieve news with embeddings from PostgreSQL."""
    
    def __init__(self, logger: StructuredLogger = None):
        """Initialize database connection."""
        self.config = load_yaml_config('settings')
        self.logger = logger or StructuredLogger(setup_logging(self.config.get('logging', {})))
        
        db_url = get_database_url()
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        self.logger.info("News storage initialized", db_url=db_url.split('@')[1] if '@' in db_url else 'localhost')
    
    def store_news(self, headline: str, content: str, embedding: np.ndarray, 
                  source: str, url: str, published_at: datetime, 
                  sentiment_score: float = None, tickers: List[str] = None) -> int:
        """
        Store a news item with embedding in PostgreSQL.
        
        Args:
            headline: News headline
            content: Full news content
            embedding: Vector embedding (numpy array)
            source: News source name
            url: URL to full article
            published_at: Publication timestamp
            sentiment_score: Optional sentiment score (-1 to 1)
            tickers: Related stock tickers
        
        Returns:
            ID of stored news item
        """
        try:
            # Convert embedding to list for PostgreSQL
            embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
            
            query = text("""
                INSERT INTO news (headline, content, source, url, published_at, 
                                 sentiment_score, embedding, tickers, ingested_at)
                VALUES (:headline, :content, :source, :url, :published_at, 
                        :sentiment_score, :embedding, :tickers, :ingested_at)
                RETURNING id
            """)
            
            with self.engine.begin() as conn:
                result = conn.execute(query, {
                    'headline': headline[:500],  # Limit headline length
                    'content': content[:2000],   # Limit content length
                    'source': source,
                    'url': url,
                    'published_at': published_at,
                    'sentiment_score': sentiment_score,
                    'embedding': embedding_list,  # pgvector will handle it
                    'tickers': tickers or [],
                    'ingested_at': datetime.utcnow()
                })
                news_id = result.scalar()
            
            self.logger.debug(f"Stored news: {headline[:50]}", 
                            news_id=news_id, source=source)
            return news_id
            
        except Exception as e:
            self.logger.error(f"Failed to store news: {e}", 
                            headline=headline[:50], error=str(e))
            raise
    
    def batch_store_news(self, news_items: List[Dict[str, Any]]) -> int:
        """
        Store multiple news items with embeddings.
        
        Args:
            news_items: List of dicts with keys:
                - headline, content, embedding, source, url, published_at
                - Optional: sentiment_score, tickers
        
        Returns:
            Number of successfully stored items
        """
        count = 0
        for item in news_items:
            try:
                self.store_news(
                    headline=item['headline'],
                    content=item['content'],
                    embedding=item['embedding'],
                    source=item['source'],
                    url=item.get('url', ''),
                    published_at=item['published_at'],
                    sentiment_score=item.get('sentiment_score'),
                    tickers=item.get('tickers', [])
                )
                count += 1
            except Exception as e:
                self.logger.warning(f"Failed to store news item: {e}")
                continue
        
        self.logger.info(f"Batch stored {count}/{len(news_items)} news items", 
                        stored_count=count, total_count=len(news_items))
        return count
    
    def search_similar_news(self, embedding: np.ndarray, ticker: str = None, 
                           limit: int = 5, similarity_threshold: float = 0.5) -> List[Dict[str, Any]]:
        """
        Search for similar news using vector similarity.
        
        Args:
            embedding: Query embedding vector
            ticker: Optional ticker to filter by
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of similar news items with similarity scores
        """
        try:
            embedding_list = embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
            
            # Build query
            query = text("""
                SELECT id, headline, content, source, url, published_at,
                       sentiment_score,
                       1 - (embedding <=> :embedding::vector) as similarity
                FROM news
                WHERE (:ticker IS NULL OR :ticker = ANY(tickers))
                  AND (1 - (embedding <=> :embedding::vector)) >= :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            
            with self.engine.connect() as conn:
                results = conn.execute(query, {
                    'embedding': embedding_list,
                    'ticker': ticker,
                    'threshold': similarity_threshold,
                    'limit': limit
                }).fetchall()
            
            items = [dict(row._mapping) for row in results]
            self.logger.debug(f"Found {len(items)} similar news items", 
                            ticker=ticker, count=len(items))
            return items
            
        except Exception as e:
            self.logger.error(f"Failed to search similar news: {e}", error=str(e))
            return []
    
    def get_news_for_ticker(self, ticker: str, hours_lookback: int = 24, 
                           limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent news for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            hours_lookback: Only return news from last N hours
            limit: Maximum number of results
        
        Returns:
            List of news items for the ticker
        """
        try:
            query = text("""
                SELECT id, headline, content, source, url, published_at, sentiment_score
                FROM news
                WHERE :ticker = ANY(tickers)
                  AND published_at >= NOW() - INTERVAL '1 hour' * :hours
                ORDER BY published_at DESC
                LIMIT :limit
            """)
            
            with self.engine.connect() as conn:
                results = conn.execute(query, {
                    'ticker': ticker,
                    'hours': hours_lookback,
                    'limit': limit
                }).fetchall()
            
            items = [dict(row._mapping) for row in results]
            self.logger.debug(f"Retrieved {len(items)} news items for {ticker}")
            return items
            
        except Exception as e:
            self.logger.error(f"Failed to get news for {ticker}: {e}")
            return []
    
    def get_news_count(self) -> int:
        """Get total count of stored news items."""
        try:
            query = text("SELECT COUNT(*) as count FROM news")
            with self.engine.connect() as conn:
                result = conn.execute(query).scalar()
            return result
        except Exception as e:
            self.logger.warning(f"Failed to get news count: {e}")
            return 0


def store_news(headline: str, content: str, embedding: np.ndarray, 
              source: str, url: str, published_at: datetime) -> int:
    """Convenience function to store single news item."""
    storage = NewsStorage()
    return storage.store_news(headline, content, embedding, source, url, published_at)


if __name__ == "__main__":
    # Test script
    storage = NewsStorage()
    count = storage.get_news_count()
    print(f"Total news items in database: {count}")

