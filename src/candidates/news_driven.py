"""
News-Driven Candidate Selection

Selects candidates based on recent news sentiment and novelty.
High sentiment or novelty articles suggest trading opportunities.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.news.storage import NewsStorage
from src.news.rag import NewsRAG
from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


class NewsDriver:
    """Select candidates based on news sentiment and novelty."""
    
    def __init__(self, logger=None):
        """Initialize news-driven selector."""
        if logger is None:
            config = load_yaml_config('settings')
            logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        self.logger = logger
        self.storage = NewsStorage()
        self.rag = NewsRAG()
    
    def select_candidates(self, 
                         hours_lookback: int = 24,
                         sentiment_threshold: float = 0.3,
                         novelty_threshold: float = 0.6) -> Dict[str, Dict]:
        """
        Select candidates based on news sentiment and novelty.
        
        Args:
            hours_lookback: Hours to look back for news (default: 24)
            sentiment_threshold: Absolute sentiment threshold (default: 0.3)
            novelty_threshold: Novelty score threshold (default: 0.6)
        
        Returns:
            Dict[ticker] -> {reason, sentiment, novelty, count}
        """
        
        candidates = {}
        
        try:
            # TODO: This requires fetching from the news database with SQLAlchemy
            # Currently the pipeline stores news articles, but accessing them requires
            # proper database URL and table schema
            
            # For Phase 3 MVP, return empty to allow other selectors to work
            # Phase 4 will fully integrate news-driven selection
            
            self.logger.info(
                f"News-driven selection: deferred to Phase 4 (requires DB query refinement)",
                extra={'status': 'pending_db_integration'}
            )
            
        except Exception as e:
            self.logger.error(f"News-driven selection failed: {e}")
            # Don't raise - allow pipeline to continue with other strategies
        
        return candidates


def get_news_driven_candidates(hours_lookback: int = 24) -> Dict[str, Dict]:
    """
    Standalone function to get news-driven candidates.
    
    Args:
        hours_lookback: Hours to look back for news
    
    Returns:
        Dict of candidates with reasons and scores
    """
    driver = NewsDriver()
    return driver.select_candidates(hours_lookback=hours_lookback)
