#!/usr/bin/env python
"""
Live Demo: Real-time news ingestion and RAG queries
Fetches actual news, processes it, and demonstrates intelligent retrieval
"""

import os
import sys

os.environ['DATABASE_URL'] = 'postgresql+psycopg2://market:market@localhost:5433/marketdb'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.news.fetcher import NewsFetcher
from src.news.parser import NewsParser
from src.news.embedder import NewsEmbedder
from src.news.storage import NewsStorage
from src.news.rag import NewsRAG
from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


def print_header(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_section(title):
    print(f"\n{title}")
    print("-"*80)


def main():
    config = load_yaml_config('settings')
    logger = StructuredLogger(setup_logging(config.get('logging', {})))
    
    print_header("LIVE NEWS PIPELINE DEMO")
    print("Fetching real financial news and demonstrating RAG capabilities...")
    
    # Initialize components
    fetcher = NewsFetcher(logger)
    parser = NewsParser(logger, use_ollama=False, use_finbert=True)
    embedder = NewsEmbedder()
    storage = NewsStorage()
    rag = NewsRAG()
    
    print(f"  Ticker extraction: LLM (Ollama) available: {fetcher.ticker_extractor.ollama_available}")
    
    # === STEP 1: Fetch live news ===
    print_section("📰 FETCHING LIVE NEWS")
    raw_news = fetcher.fetch_all_feeds(hours_lookback=48)  # Last 48 hours
    print(f"✓ Fetched {len(raw_news)} articles from RSS feeds")
    print(f"✓ Tickers extracted using: {'LLM (Ollama)' if fetcher.ticker_extractor.ollama_available else 'Fallback Mapping'}")
    
    if not raw_news:
        print("⚠️  No news fetched from RSS feeds")
        print("Creating sample data for demo...")
        raw_news = [
            {
                'headline': 'Apple Q1 2026 Earnings Exceed Expectations with Record iPhone Sales',
                'content': 'Apple Inc. reported stellar first-quarter results driven by robust iPhone demand and growing services revenue. The tech giant beat analyst estimates across all key metrics.',
                'tickers': ['AAPL'],
                'source': 'Financial Times',
                'url': 'https://example.com/apple-earnings',
                'published_at': None
            },
            {
                'headline': 'Tesla Announces 25% Drop in Q4 Deliveries Amid Production Issues',
                'content': 'Tesla reported lower-than-expected vehicle deliveries for Q4 due to supply chain disruptions and factory downtime. Investors reacted negatively to the news.',
                'tickers': ['TSLA'],
                'source': 'Reuters',
                'url': 'https://example.com/tesla-deliveries',
                'published_at': None
            },
            {
                'headline': 'Microsoft and OpenAI Expand Partnership with $10B Investment',
                'content': 'Microsoft announced a major expansion of its partnership with OpenAI, committing $10 billion to accelerate AI development and integration across its product suite.',
                'tickers': ['MSFT'],
                'source': 'Bloomberg',
                'url': 'https://example.com/msft-openai',
                'published_at': None
            },
            {
                'headline': 'Nvidia GPU Shortage Continues as AI Demand Surges',
                'content': 'Nvidia faces ongoing supply constraints for its latest GPU chips as data centers race to build AI infrastructure. The company expects tight supply through 2026.',
                'tickers': ['NVDA'],
                'source': 'TechCrunch',
                'url': 'https://example.com/nvidia-shortage',
                'published_at': None
            },
            {
                'headline': 'Amazon Web Services Reports 28% Revenue Growth in Cloud Computing',
                'content': 'AWS continues to dominate cloud computing with strong growth despite increased competition. The division remains Amazon\'s most profitable business unit.',
                'tickers': ['AMZN'],
                'source': 'CNBC',
                'url': 'https://example.com/aws-growth',
                'published_at': None
            },
        ]
    
    print("\nSample Headlines:")
    for i, item in enumerate(raw_news[:5], 1):
        ticker_str = ', '.join(item.get('tickers', []))
        print(f"  {i}. [{ticker_str}] {item['headline'][:60]}")
    
    # === STEP 2: Parse sentiment ===
    print_section("🎯 ANALYZING SENTIMENT")
    parsed_news = []
    for item in raw_news:
        headline = item.get('headline', '')
        content = item.get('content', '')
        
        sentiment = parser.extract_sentiment(headline + ' ' + content, use_llm=False)
        
        parsed_news.append({
            **item,
            'sentiment_score': sentiment,
            'novelty_score': 0.75
        })
    
    print(f"✓ Analyzed sentiment for {len(parsed_news)} articles")
    bullish = sum(1 for item in parsed_news if item['sentiment_score'] > 0.3)
    bearish = sum(1 for item in parsed_news if item['sentiment_score'] < -0.3)
    neutral = len(parsed_news) - bullish - bearish
    
    print(f"\nSentiment Distribution:")
    print(f"  📈 Bullish: {bullish} articles")
    print(f"  📉 Bearish: {bearish} articles")
    print(f"  ➡️  Neutral: {neutral} articles")
    
    # === STEP 3: Generate embeddings ===
    print_section("🧠 GENERATING EMBEDDINGS")
    texts = [f"{item['headline']} {item.get('content', '')}" for item in parsed_news]
    embeddings = embedder.batch_embed(texts)
    
    for i, item in enumerate(parsed_news):
        item['embedding'] = embeddings[i]
    
    print(f"✓ Generated {len(embeddings)} embeddings ({embedder.embedding_dim} dimensions)")
    
    # === STEP 4: Store in database ===
    print_section("💾 STORING IN DATABASE")
    initial_count = storage.get_news_count()
    
    stored_ids = []
    for item in parsed_news:
        try:
            news_id = storage.store_news(
                headline=item['headline'],
                content=item.get('content', ''),
                source=item.get('source', 'Unknown'),
                url=item.get('url', ''),
                tickers=item.get('tickers', []),
                embedding=item['embedding'],
                sentiment_score=item['sentiment_score'],
                published_at=item.get('published_at')
            )
            stored_ids.append(news_id)
        except Exception as e:
            logger.warning(f"Failed to store article: {e}")
    
    final_count = storage.get_news_count()
    print(f"✓ Stored {len(stored_ids)} articles")
    print(f"  Database: {initial_count} → {final_count} total articles")
    
    # === STEP 5: RAG Demonstrations ===
    print_header("RAG INTELLIGENCE DEMO")
    
    # Demo 1: Semantic search
    print_section("🔍 SEMANTIC SEARCH DEMO")
    queries = [
        "earnings beat expectations revenue growth",
        "production problems supply chain delays",
        "artificial intelligence partnership",
    ]
    
    for query in queries:
        print(f"\n💬 Query: \"{query}\"")
        results = rag.retrieve_similar_news(query, limit=3, recency_weight=0.3)
        if results:
            print(f"   Found {len(results)} similar articles:")
            for i, result in enumerate(results, 1):
                score = result.get('score', 0)
                print(f"   {i}. {result['headline'][:55]}")
                print(f"      Score: {score:.3f}, Sentiment: {result.get('sentiment_score', 0):+.2f}")
        else:
            print("   No similar articles found")
    
    # Demo 2: Ticker analysis
    print_section("📊 TICKER SENTIMENT ANALYSIS")
    tickers = set()
    for item in parsed_news:
        tickers.update(item.get('tickers', []))
    
    tickers = list(tickers)[:5]  # Top 5 tickers
    
    for ticker in tickers:
        context = rag.get_ticker_context(ticker, max_hours=168)
        
        if context['count'] > 0:
            emoji = "📈" if context['avg_sentiment'] > 0.2 else ("📉" if context['avg_sentiment'] < -0.2 else "➡️")
            print(f"\n{emoji} {ticker}")
            print(f"   Articles: {context['count']}")
            print(f"   Avg Sentiment: {context['avg_sentiment']:+.2f}")
            print(f"   Trend: {context['sentiment_trend']}")
            
            if context['news_items']:
                latest = context['news_items'][0]
                print(f"   Latest: {latest['headline'][:50]}")
    
    # Demo 3: Sector analysis
    if len(tickers) >= 2:
        print_section("🏢 SECTOR ANALYSIS")
        sector_tickers = tickers[:3]
        sector = rag.get_sector_context(sector_tickers, max_hours=168)
        
        print(f"\nAnalyzing sector: {', '.join(sector_tickers)}")
        print(f"  Total articles: {sector['count']}")
        print(f"  Avg sentiment: {sector['avg_sentiment']:+.2f}")
        print(f"  Bullish: {sector['bullish_items']}, Bearish: {sector['bearish_items']}")
        print(f"  Sentiment balance: {sector['sentiment_balance']:+.0f}")
        
        if sector['avg_sentiment'] > 0.3:
            signal = "🟢 BULLISH sector sentiment - Consider long positions"
        elif sector['avg_sentiment'] < -0.3:
            signal = "🔴 BEARISH sector sentiment - Consider reducing exposure"
        else:
            signal = "🟡 NEUTRAL sector sentiment - Hold current positions"
        
        print(f"\n  Trading Signal: {signal}")
    
    # === SUMMARY ===
    print_header("DEMO SUMMARY")
    print(f"""
✅ Successfully processed {len(raw_news)} news articles
✅ Generated {len(embeddings)} semantic embeddings
✅ Stored in PostgreSQL with pgvector
✅ RAG retrieval operational for {len(tickers)} tickers

The system can now:
  • Fetch real-time financial news
  • Extract sentiment and generate embeddings
  • Perform semantic similarity search
  • Aggregate sentiment by ticker and sector
  • Provide context for agent decision-making

Ready for Phase 3: Candidates Selection & ML Training
    """)
    print("="*80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
