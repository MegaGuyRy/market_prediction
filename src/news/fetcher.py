"""
News Fetcher Module
Handles RSS feed fetching and news source integration.

Fetches financial news from RSS feeds configured in settings.yaml
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
import feedparser

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import load_yaml_config
from utils.logging import StructuredLogger, setup_logging


class NewsFetcher:
    """Fetches news from configured RSS feeds."""
    
    def __init__(self, logger: StructuredLogger = None):
        """Initialize fetcher with configured news sources."""
        self.config = load_yaml_config('settings')
        self.rss_feeds = self.config.get('data', {}).get('news_sources', [])
        self.logger = logger or StructuredLogger(setup_logging(self.config.get('logging', {})))
    
    def fetch_all_feeds(self, hours_lookback: int = 24) -> List[Dict[str, Any]]:
        """
        Fetch all configured RSS feeds.
        
        Args:
            hours_lookback: Only fetch news from last N hours
        
        Returns:
            List of parsed news items
        """
        all_items = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_lookback)
        
        for feed_url in self.rss_feeds:
            try:
                self.logger.info(f"Fetching RSS feed: {feed_url}")
                items = self.fetch_rss_feed(feed_url, cutoff_time)
                all_items.extend(items)
                self.logger.info(f"Fetched {len(items)} items from {feed_url}")
            except Exception as e:
                self.logger.error(f"Failed to fetch {feed_url}: {e}", 
                                 feed_url=feed_url, error=str(e))
        
        self.logger.info(f"Total items fetched: {len(all_items)}", 
                        item_count=len(all_items))
        return all_items
    
    def fetch_rss_feed(self, feed_url: str, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """
        Fetch single RSS feed.
        
        Args:
            feed_url: URL of RSS feed
            cutoff_time: Only return items published after this time
        
        Returns:
            List of parsed news items
        """
        feed = feedparser.parse(feed_url)
        items = []
        
        if feed.bozo:
            self.logger.warning(f"Feed parsing error: {feed.bozo_exception}", 
                              feed_url=feed_url)
        
        for entry in feed.entries:
            try:
                # Extract published time
                pub_time = None
                if hasattr(entry, 'published_parsed'):
                    pub_time = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed'):
                    pub_time = datetime(*entry.updated_parsed[:6])
                
                # Skip if too old
                if pub_time and pub_time < cutoff_time:
                    continue
                
                item = {
                    'headline': entry.get('title', 'No title'),
                    'content': entry.get('summary', entry.get('description', '')),
                    'url': entry.get('link', ''),
                    'source': feed.feed.get('title', feed_url),
                    'published_at': pub_time or datetime.utcnow(),
                    'feed_url': feed_url
                }
                items.append(item)
                
            except Exception as e:
                self.logger.warning(f"Failed to parse feed entry: {e}", 
                                   error=str(e))
                continue
        
        return items


def fetch_rss_feeds(hours_lookback: int = 24) -> List[Dict[str, Any]]:
    """
    Convenience function to fetch all configured RSS feeds.
    
    Args:
        hours_lookback: Only fetch news from last N hours
    
    Returns:
        List of news items
    """
    fetcher = NewsFetcher()
    return fetcher.fetch_all_feeds(hours_lookback)


if __name__ == "__main__":
    # Test script
    fetcher = NewsFetcher()
    items = fetcher.fetch_all_feeds(hours_lookback=24)
    print(f"Fetched {len(items)} items")
    for item in items:
        print(f"  - {item['headline'][:80]} ({item['source']})")

