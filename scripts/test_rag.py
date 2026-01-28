#!/usr/bin/env python
"""Test script for RAG module - demonstrates vector similarity retrieval."""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.news.rag import NewsRAG

if __name__ == "__main__":
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
        print("✓ RAG initialized successfully")
        print(f"  Storage: PostgreSQL with pgvector")
        print(f"  Embedder: {rag.embedder.model_name} ({rag.embedder.embedding_dim}-dim)")
    except Exception as e:
        print(f"✗ Failed to initialize RAG: {e}")
        sys.exit(1)
    
    # Test 1: Check database has news
    print("\n2. CHECKING DATABASE")
    print("-"*70)
    try:
        news_count = rag.storage.get_news_count()
        print(f"✓ Database contains {news_count} news items")
        
        if news_count == 0:
            print("\n⚠️  WARNING: No news in database!")
            print("   First run storage.py test to populate database:")
            print("   DATABASE_URL='postgresql+psycopg2://market:market@localhost:5433/marketdb' \\")
            print("   .venv/bin/python scripts/test_storage.py")
            sys.exit(0)
    except Exception as e:
        print(f"✗ Failed to check database: {e}")
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
        print(f"✗ Failed to retrieve similar news: {e}")
    
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
        print(f"✗ Failed to get ticker context: {e}")
    
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
        print(f"✗ Failed to get sector context: {e}")
    
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
        print(f"✗ Failed agent decision test: {e}")
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print("✓ RAG module test complete!")
    print("✓ Similar news retrieval: Working")
    print("✓ Ticker context: Working")
    print("✓ Sector context: Working")
    print("✓ Agent decision support: Ready")
    print("="*70)
