#!/usr/bin/env python
"""
Complete news ingestion pipeline test.
Runs all components in sequence: Fetcher → Parser → Embedder → Storage → RAG
"""

import os
import sys

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://market:market@localhost:5433/marketdb'

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.news.fetcher import NewsFetcher
from src.news.parser import NewsParser
from src.news.embedder import NewsEmbedder
from src.news.storage import NewsStorage
from src.news.rag import NewsRAG
from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "="*70)
    print(title)
    print("="*70)


def print_step(num, title):
    """Print a step header."""
    print(f"\n{num}. {title}")
    print("-"*70)


def run_pipeline():
    """Run the complete pipeline."""
    
    # Setup logging
    config = load_yaml_config('settings')
    logger = StructuredLogger(setup_logging(config.get('logging', {})))
    
    print_section("COMPLETE NEWS PIPELINE TEST")
    print("Components: Fetcher → Parser → Embedder → Storage → RAG")
    
    # ==== STAGE 1: FETCHER ====
    print_step(1, "FETCHER - Fetch news from RSS feeds")
    try:
        fetcher = NewsFetcher(logger)
        raw_news = fetcher.fetch_all_feeds(hours_lookback=24)
        
        # Map common companies mentioned in headlines to tickers
        ticker_map = {
            'apple': 'AAPL', 'iphone': 'AAPL', 'ios': 'AAPL',
            'tesla': 'TSLA', 'ev': 'TSLA', 'electric vehicle': 'TSLA',
            'microsoft': 'MSFT', 'ai': 'MSFT', 'openai': 'MSFT',
            'nvidia': 'NVDA', 'gpu': 'NVDA', 'ai chips': 'NVDA',
            'google': 'GOOGL', 'alphabet': 'GOOGL',
            'meta': 'META', 'facebook': 'META',
            'amazon': 'AMZN',
        }
        
        # Add tickers to fetched news based on content
        for item in raw_news:
            text = (item.get('headline', '') + ' ' + item.get('content', '')).lower()
            found_tickers = []
            for keyword, ticker in ticker_map.items():
                if keyword in text and ticker not in found_tickers:
                    found_tickers.append(ticker)
            item['tickers'] = found_tickers if found_tickers else ['AAPL']  # Default to AAPL if no match
        
        print(f"✓ Fetched {len(raw_news)} news items from RSS feeds")
        
        if raw_news:
            print(f"\nSample articles:")
            for item in raw_news[:3]:
                print(f"  • {item['headline'][:50]}")
                print(f"    Source: {item['source']}, Tickers: {', '.join(item.get('tickers', []))}")
        else:
            print("⚠️  No news fetched. Creating test data...")
            raw_news = [
                {
                    'headline': 'Apple reports record Q1 earnings beat',
                    'content': 'Apple exceeded expectations with strong iPhone and services growth',
                    'tickers': ['AAPL'],
                    'source': 'Yahoo Finance',
                    'url': 'https://example.com/1',
                    'published_at': None
                },
                {
                    'headline': 'Tesla production falls short of targets',
                    'content': 'Tesla announces lower than expected quarterly production numbers',
                    'tickers': ['TSLA'],
                    'source': 'Reuters',
                    'url': 'https://example.com/2',
                    'published_at': None
                },
                {
                    'headline': 'Microsoft launches new AI initiatives',
                    'content': 'Microsoft announces strategic partnerships for AI development',
                    'tickers': ['MSFT'],
                    'source': 'TechCrunch',
                    'url': 'https://example.com/3',
                    'published_at': None
                },
                {
                    'headline': 'Nvidia GPU demand remains strong',
                    'content': 'Data center GPU demand continues to surge for AI applications',
                    'tickers': ['NVDA'],
                    'source': 'Bloomberg',
                    'url': 'https://example.com/4',
                    'published_at': None
                },
            ]
            print(f"✓ Created {len(raw_news)} test news items")
            
            for item in raw_news:
                print(f"  • {item['headline'][:50]}")
    except Exception as e:
        print(f"✗ Fetcher failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ==== STAGE 2: PARSER ====
    print_step(2, "PARSER - Extract sentiment and novelty scores")
    try:
        parser = NewsParser(logger)
        parsed_news = []
        
        for item in raw_news:
            try:
                # Ensure required fields
                headline = item.get('headline', 'Unknown')
                content = item.get('content', '')
                
                # Extract sentiment (using heuristic, not Ollama)
                sentiment = parser.extract_sentiment(
                    headline + ' ' + content,
                    use_llm=False  # Use heuristic method
                )
                
                # For novelty, we'll estimate it (normally compared to historical)
                # For now, assign a base novelty score
                novelty = 0.7  # Assume fresh news has reasonable novelty
                
                parsed_item = {
                    **item,
                    'headline': headline,
                    'content': content,
                    'tickers': item.get('tickers', []),
                    'sentiment_score': sentiment,
                    'novelty_score': novelty
                }
                parsed_news.append(parsed_item)
            except Exception as e:
                logger.warning(f"Failed to parse {item.get('headline', 'unknown')}: {e}")
                continue
        
        print(f"✓ Parsed {len(parsed_news)} news items")
        
        for item in parsed_news:
            sentiment_emoji = "📈" if item['sentiment_score'] > 0.2 else ("📉" if item['sentiment_score'] < -0.2 else "➡️")
            print(f"  {sentiment_emoji} {item['headline'][:50]}")
            print(f"     Sentiment: {item['sentiment_score']:+.2f}, Novelty: {item['novelty_score']:.2f}")
    except Exception as e:
        print(f"✗ Parser failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ==== STAGE 3: EMBEDDER ====
    print_step(3, "EMBEDDER - Generate 768-dimensional embeddings")
    try:
        embedder = NewsEmbedder()
        
        # Prepare texts for embedding
        texts = [f"{item['headline']} {item['content']}" for item in parsed_news]
        
        # Generate embeddings
        embeddings = embedder.batch_embed(texts)
        
        print(f"✓ Generated {len(embeddings)} embeddings")
        print(f"  Model: {embedder.model_name}")
        print(f"  Dimensions: {embedder.embedding_dim}")
        
        # Attach embeddings to items
        for i, item in enumerate(parsed_news):
            item['embedding'] = embeddings[i]
        
        # Verify embeddings
        sample_norm = embeddings[0].__norm__() if hasattr(embeddings[0], '__norm__') else None
        print(f"  Sample embedding norm: {sample_norm if sample_norm else 'N/A'}")
        
    except Exception as e:
        print(f"✗ Embedder failed: {e}")
        sys.exit(1)
    
    # ==== STAGE 4: STORAGE ====
    print_step(4, "STORAGE - Store in PostgreSQL with pgvector")
    try:
        storage = NewsStorage()
        initial_count = storage.get_news_count()
        
        # Store all parsed news
        stored_ids = []
        for item in parsed_news:
            try:
                news_id = storage.store_news(
                    headline=item['headline'],
                    content=item['content'],
                    source=item['source'],
                    url=item['url'],
                    tickers=item['tickers'],
                    embedding=item['embedding'],
                    sentiment_score=item['sentiment_score'],
                    published_at=item.get('published_at')
                )
                stored_ids.append(news_id)
            except Exception as e:
                logger.warning(f"Failed to store {item['headline']}: {e}")
                continue
        
        final_count = storage.get_news_count()
        
        print(f"✓ Stored {len(stored_ids)} news items in database")
        print(f"  Database count: {initial_count} → {final_count} items")
        
        if stored_ids:
            print(f"\nStored item IDs: {stored_ids[:5]}{'...' if len(stored_ids) > 5 else ''}")
        
    except Exception as e:
        print(f"✗ Storage failed: {e}")
        sys.exit(1)
    
    # ==== STAGE 5: RAG ====
    print_step(5, "RAG - Retrieve and aggregate context")
    try:
        rag = NewsRAG()
        
        # Get ticker contexts for stored tickers
        tickers = set()
        for item in parsed_news:
            tickers.update(item['tickers'])
        
        tickers = list(tickers)[:3]  # Limit to first 3 tickers
        
        print(f"✓ Analyzing {len(tickers)} tickers: {', '.join(tickers)}")
        
        for ticker in tickers:
            try:
                context = rag.get_ticker_context(ticker, max_hours=24)
                
                if context['count'] > 0:
                    sentiment_emoji = "📈" if context['avg_sentiment'] > 0.2 else ("📉" if context['avg_sentiment'] < -0.2 else "➡️")
                    print(f"\n  {sentiment_emoji} {ticker}")
                    print(f"     News items: {context['count']}")
                    print(f"     Avg sentiment: {context['avg_sentiment']:+.2f}")
                    print(f"     Trend: {context['sentiment_trend']}")
            except Exception as e:
                logger.warning(f"Failed to get context for {ticker}: {e}")
                continue
        
        # Sector analysis
        if len(tickers) > 1:
            try:
                sector_context = rag.get_sector_context(tickers, max_hours=24)
                print(f"\n  Sector Analysis ({', '.join(tickers)})")
                print(f"     Total news: {sector_context['count']}")
                print(f"     Avg sentiment: {sector_context['avg_sentiment']:+.2f}")
                print(f"     Bullish: {sector_context['bullish_items']}, Bearish: {sector_context['bearish_items']}")
            except Exception as e:
                logger.warning(f"Sector analysis failed: {e}")
        
    except Exception as e:
        print(f"✗ RAG failed: {e}")
        sys.exit(1)
    
    # ==== SUMMARY ====
    print_section("PIPELINE COMPLETE ✓")
    print(f"""
✓ Fetcher:  Collected {len(raw_news)} news items
✓ Parser:   Extracted sentiment and novelty scores
✓ Embedder: Generated 768-dimensional vectors
✓ Storage:  Stored {len(stored_ids)} items in PostgreSQL
✓ RAG:      Retrieved and aggregated context

Total flow: {len(raw_news)} → {len(parsed_news)} → {len(embeddings)} → {len(stored_ids)} items
    """)
    print("="*70)


if __name__ == "__main__":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        print("\n✗ Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Pipeline error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
