#!/usr/bin/env python
"""
Test news ingestion pipeline end-to-end.
Tests: fetcher -> embedder -> parser -> storage -> RAG
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure local database URL if not provided (for host runs)
if not os.getenv('DATABASE_URL'):
    os.environ['DATABASE_URL'] = 'postgresql+psycopg2://market:market@localhost:5433/marketdb'

from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config
from src.news.fetcher import NewsFetcher
from src.news.embedder import NewsEmbedder
from src.news.parser import NewsParser
from src.news.storage import NewsStorage
from src.news.rag import NewsRAG


def test_fetcher():
    """Test news fetching from RSS feeds."""
    print("\n" + "="*60)
    print("TEST 1: News Fetcher")
    print("="*60)
    
    try:
        config = load_yaml_config('settings')
        logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        fetcher = NewsFetcher(logger)
        news_items = fetcher.fetch_all_feeds(hours_lookback=168)  # 1 week
        
        print(f"✓ Fetched {len(news_items)} news items")
        
        if news_items:
            sample = news_items[0]
            print(f"  Sample headline: {sample.get('headline', 'N/A')[:60]}...")
            print(f"  Sample source: {sample.get('source', 'N/A')}")
            print(f"  Sample URL: {sample.get('url', 'N/A')[:60]}...")
        
        return news_items
        
    except Exception as e:
        print(f"✗ Fetcher test failed: {e}")
        return []


def test_embedder(news_items):
    """Test news embedding generation."""
    print("\n" + "="*60)
    print("TEST 2: News Embedder")
    print("="*60)
    
    try:
        config = load_yaml_config('settings')
        logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        embedder = NewsEmbedder(logger)
        
        # Test single embedding
        test_text = "Apple beats earnings with strong iPhone sales"
        embedding = embedder.embed_text(test_text)
        
        print(f"✓ Single embedding generated")
        print(f"  Embedding shape: {embedding.shape}")
        print(f"  L2 norm: {np.linalg.norm(embedding):.4f}")
        
        # Test batch embedding
        if news_items:
            texts = [f"{item.get('headline', '')} {item.get('content', '')[:100]}"
                    for item in news_items[:5]]
            embeddings = embedder.batch_embed(texts)
            
            print(f"✓ Batch embeddings generated")
            print(f"  Processed: {len(embeddings)} items")
            print(f"  First embedding norm: {np.linalg.norm(embeddings[0]):.4f}")
            
            # Add embeddings to news items
            for i, item in enumerate(news_items[:5]):
                if i < len(embeddings):
                    news_items[i]['embedding'] = embeddings[i]
        
        return embedder
        
    except Exception as e:
        print(f"✗ Embedder test failed: {e}")
        return None


def test_parser(news_items):
    """Test sentiment and novelty extraction."""
    print("\n" + "="*60)
    print("TEST 3: News Parser")
    print("="*60)
    
    try:
        config = load_yaml_config('settings')
        logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        parser = NewsParser(logger, use_ollama=False)  # Use heuristic for testing
        
        # Test sentiment extraction
        test_texts = [
            "Apple beats earnings expectations",
            "Tesla stock crashes after missing targets",
            "Microsoft announces partnership"
        ]
        
        print("✓ Sentiment extraction:")
        for text in test_texts:
            sentiment = parser.extract_sentiment(text, use_llm=False)
            print(f"  '{text}' -> {sentiment:.2f}")
        
        # Test novelty scoring
        if news_items and 'embedding' in news_items[0]:
            embeddings = [item.get('embedding') for item in news_items[:5]
                         if 'embedding' in item]
            if embeddings:
                test_embedding = embeddings[0]
                novelty = parser.score_novelty("Test headline", test_embedding, embeddings[1:])
                print(f"\n✓ Novelty scoring: {novelty:.2f}")
        
        # Test batch parsing
        if news_items and len(news_items) >= 3:
            for item in news_items[:3]:
                if 'embedding' not in item:
                    item['embedding'] = np.zeros(768)
            
            parsed = parser.batch_parse_news(news_items[:3])
            print(f"\n✓ Batch parsed {len(parsed)} items")
            for i, item in enumerate(parsed):
                print(f"  Item {i}: sentiment={item.get('sentiment_score', 0):.2f}, "
                      f"novelty={item.get('novelty_score', 0):.2f}")
        
        return parser
        
    except Exception as e:
        print(f"✗ Parser test failed: {e}")
        return None


def test_storage(news_items):
    """Test storing news with embeddings."""
    print("\n" + "="*60)
    print("TEST 4: News Storage")
    print("="*60)
    
    try:
        config = load_yaml_config('settings')
        logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        storage = NewsStorage(logger)
        
        # Get initial count
        initial_count = storage.get_news_count()
        print(f"✓ Database connected (existing news: {initial_count})")
        
        # Store sample news items
        stored_count = 0
        for i, item in enumerate(news_items[:3]):
            if 'embedding' not in item:
                item['embedding'] = np.zeros(768)
            
            try:
                news_id = storage.store_news(
                    headline=item.get('headline', 'Unknown'),
                    content=item.get('content', ''),
                    embedding=item['embedding'],
                    source=item.get('source', 'Unknown'),
                    url=item.get('url', ''),
                    published_at=item.get('published_at', datetime.utcnow()),
                    sentiment_score=item.get('sentiment_score', 0),
                    tickers=['TEST']  # Tag with TEST ticker
                )
                stored_count += 1
            except Exception as e:
                print(f"  Warning: Failed to store item {i}: {e}")
                continue
        
        print(f"✓ Stored {stored_count} news items")
        
        # Verify storage
        new_count = storage.get_news_count()
        print(f"✓ Database now has {new_count} news items (added {new_count - initial_count})")
        
        return storage
        
    except Exception as e:
        print(f"✗ Storage test failed: {e}")
        return None


def test_rag(storage, embedder):
    """Test RAG retrieval functionality."""
    print("\n" + "="*60)
    print("TEST 5: News RAG")
    print("="*60)
    
    try:
        config = load_yaml_config('settings')
        logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        rag = NewsRAG(logger)
        
        # Test ticker context
        context = rag.get_ticker_context("TEST", max_hours=168, limit=5)
        print(f"✓ Retrieved ticker context for TEST")
        print(f"  News items: {context['count']}")
        print(f"  Avg sentiment: {context['avg_sentiment']:.2f}")
        print(f"  Sentiment trend: {context['sentiment_trend']}")
        
        # Test similar news retrieval
        if context['count'] > 0:
            query_text = "Technology earnings and partnership announcements"
            similar = rag.retrieve_similar_news(query_text, ticker="TEST", limit=3)
            print(f"\n✓ Retrieved similar news")
            print(f"  Query: '{query_text}'")
            print(f"  Similar items found: {len(similar)}")
            if similar:
                print(f"  Top match: {similar[0].get('headline', 'N/A')[:60]}...")
        
        # Test sector context
        sector = rag.get_sector_context(["TEST", "AAPL"], max_hours=168, top_k=3)
        print(f"\n✓ Retrieved sector context")
        print(f"  Total items: {sector['count']}")
        print(f"  Avg sentiment: {sector['avg_sentiment']:.2f}")
        print(f"  Bullish items: {sector['bullish_items']}")
        print(f"  Bearish items: {sector['bearish_items']}")
        
        return True
        
    except Exception as e:
        print(f"✗ RAG test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("NEWS INGESTION PIPELINE TEST SUITE")
    print("="*60)
    
    # Test sequence
    news_items = test_fetcher()
    embedder = test_embedder(news_items)
    parser = test_parser(news_items)
    storage = test_storage(news_items)
    rag_success = test_rag(storage, embedder) if storage else False
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    summary = [
        ("Fetcher", len(news_items) > 0),
        ("Embedder", embedder is not None),
        ("Parser", parser is not None),
        ("Storage", storage is not None),
        ("RAG", rag_success)
    ]
    
    passed = sum(1 for _, success in summary if success)
    total = len(summary)
    
    for name, success in summary:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nResult: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
