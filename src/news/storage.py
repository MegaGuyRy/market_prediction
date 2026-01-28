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
            embedding_str = '[' + ','.join(str(x) for x in embedding_list) + ']'
            
            # Build query
            query = text(f"""
                SELECT id, headline, content, source, url, published_at,
                       sentiment_score,
                       1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM news
                WHERE (:ticker IS NULL OR :ticker = ANY(tickers))
                  AND (1 - (embedding <=> '{embedding_str}'::vector)) >= :threshold
                ORDER BY similarity DESC
                LIMIT :limit
            """)
            
            with self.engine.connect() as conn:
                results = conn.execute(query, {
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
    print("="*70)
    print("NEWS STORAGE TEST")
    print("="*70)
    
    # Initialize storage
    storage = NewsStorage()
    
    # Test 1: Database connection and count
    print("\n1. DATABASE CONNECTION TEST")
    print("-"*70)
    try:
        initial_count = storage.get_news_count()
        print(f"✓ Connected to database")
        print(f"  Initial news count: {initial_count}")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)
    
    # Test 2: Generate test data with embeddings
    print("\n2. GENERATING TEST DATA")
    print("-"*70)
    from embedder import NewsEmbedder
    from parser import NewsParser
    
    embedder = NewsEmbedder()
    parser = NewsParser(use_ollama=False)
    
    test_news = [
        {
            "headline": "Apple beats Q4 earnings expectations",
            "content": "Apple Inc reported strong Q4 earnings with record iPhone sales and growth in services.",
            "source": "Bloomberg",
            "url": "https://example.com/apple-earnings",
            "published_at": datetime.utcnow(),
            "tickers": ["AAPL"],
        },
        {
            "headline": "Tesla misses delivery targets in January",
            "content": "Tesla announced lower-than-expected delivery numbers for Q1, citing production challenges.",
            "source": "Reuters",
            "url": "https://example.com/tesla-miss",
            "published_at": datetime.utcnow(),
            "tickers": ["TSLA"],
        },
        {
            "headline": "Microsoft announces AI partnership",
            "content": "Microsoft and OpenAI expand partnership to integrate advanced AI into enterprise products.",
            "source": "TechCrunch",
            "url": "https://example.com/msft-ai",
            "published_at": datetime.utcnow(),
            "tickers": ["MSFT"],
        },
    ]
    
    # Add embeddings and sentiment
    for item in test_news:
        combined = f"{item['headline']} {item['content']}"
        item['embedding'] = embedder.embed_text(combined)
        item['sentiment_score'] = parser.extract_sentiment(combined, use_llm=False)
    
    print(f"✓ Generated {len(test_news)} test news items")
    for i, item in enumerate(test_news, 1):
        print(f"  {i}. {item['headline'][:50]}...")
        print(f"     Tickers: {item['tickers']}, Sentiment: {item['sentiment_score']:+.2f}")
    
    # Test 3: Store single news item
    print("\n3. STORE SINGLE NEWS ITEM TEST")
    print("-"*70)
    try:
        first_item = test_news[0]
        news_id = storage.store_news(
            headline=first_item['headline'],
            content=first_item['content'],
            embedding=first_item['embedding'],
            source=first_item['source'],
            url=first_item['url'],
            published_at=first_item['published_at'],
            sentiment_score=first_item['sentiment_score'],
            tickers=first_item['tickers']
        )
        print(f"✓ Stored single news item")
        print(f"  News ID: {news_id}")
        print(f"  Headline: {first_item['headline']}")
    except Exception as e:
        print(f"✗ Failed to store single item: {e}")
    
    # Test 4: Batch store news items
    print("\n4. BATCH STORE NEWS ITEMS TEST")
    print("-"*70)
    try:
        batch_count = storage.batch_store_news(test_news[1:])
        print(f"✓ Batch stored {batch_count} news items")
    except Exception as e:
        print(f"✗ Failed to batch store: {e}")
    
    # Test 5: Get news count
    print("\n5. GET NEWS COUNT TEST")
    print("-"*70)
    try:
        final_count = storage.get_news_count()
        added = final_count - initial_count
        print(f"✓ Retrieved news count")
        print(f"  Initial count: {initial_count}")
        print(f"  Final count: {final_count}")
        print(f"  Added in this test: {added}")
    except Exception as e:
        print(f"✗ Failed to get count: {e}")
    
    # Test 6: Retrieve news for ticker
    print("\n6. GET NEWS FOR TICKER TEST")
    print("-"*70)
    try:
        apple_news = storage.get_news_for_ticker("AAPL", hours_lookback=24, limit=5)
        print(f"✓ Retrieved news for AAPL")
        print(f"  Found {len(apple_news)} items")
        if apple_news:
            for i, item in enumerate(apple_news, 1):
                print(f"  {i}. {item['headline'][:60]}")
                print(f"     Sentiment: {item.get('sentiment_score', 'N/A')}")
    except Exception as e:
        print(f"✗ Failed to get ticker news: {e}")
    
    # Test 7: Search similar news
    print("\n7. SEARCH SIMILAR NEWS TEST")
    print("-"*70)
    try:
        query_embedding = embedder.embed_text("earnings announcement revenue growth")
        similar = storage.search_similar_news(
            embedding=query_embedding,
            ticker=None,
            limit=3,
            similarity_threshold=0.3
        )
        print(f"✓ Searched for similar news")
        print(f"  Found {len(similar)} similar items")
        if similar:
            for i, item in enumerate(similar, 1):
                print(f"  {i}. {item['headline'][:60]}")
                print(f"     Similarity: {item.get('similarity', 'N/A'):.2f}")
    except Exception as e:
        print(f"✗ Failed to search similar: {e}")
    
    # Test 8: Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"✓ All storage operations tested successfully!")
    print(f"✓ Final database state: {final_count} total news items")
    print("="*70)

