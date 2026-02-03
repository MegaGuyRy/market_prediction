"""
Candidate Selector Module - Main Orchestrator

Combines four selection strategies:
1. News-Driven: High sentiment/novelty articles
2. Market-Driven: Technical anomalies (gaps, volume)
3. Portfolio-Driven: Open positions (mandatory)
4. Baseline: Rotating coverage of blue-chips
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.candidates.news_driven import NewsDriver
from src.candidates.market_driven import MarketDriver
from src.candidates.portfolio_driven import PortfolioDriver
from src.candidates.baseline import BaselineRotator
from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


class CandidateSelector:
    """Orchestrates candidate selection from multiple strategies."""
    
    def __init__(self, logger=None):
        """Initialize selector with sub-components."""
        if logger is None:
            config = load_yaml_config('settings')
            logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        self.logger = logger
        self.news_driver = NewsDriver(logger)
        self.market_driver = MarketDriver(logger)
        self.portfolio_driver = PortfolioDriver(logger)
        self.baseline_rotator = BaselineRotator(logger)
    
    def select_candidates(self,
                         hours_lookback: int = 24,
                         baseline_size: int = 10) -> List[Tuple[str, str, float]]:
        """
        Select candidates from all four strategies.
        
        Args:
            hours_lookback: Hours to look back for news
            baseline_size: Number of baseline candidates per day
        
        Returns:
            List of (ticker, reason, priority_score) tuples, sorted by priority
        """
        
        all_candidates = {}
        
        try:
            # Strategy 1: News-Driven (High Priority)
            self.logger.info("Selecting candidates: News-Driven...")
            news_candidates = self.news_driver.select_candidates(hours_lookback=hours_lookback)
            for ticker, info in news_candidates.items():
                all_candidates[ticker] = {
                    'reason': info['reason'],
                    'priority': 0.9,  # Highest priority
                    'source': 'news',
                    'score': abs(info.get('sentiment', 0)),
                    'details': info
                }
            
            # Strategy 2: Market-Driven (High Priority)
            self.logger.info("Selecting candidates: Market-Driven...")
            market_candidates = self.market_driver.select_candidates()
            for ticker, info in market_candidates.items():
                if ticker in all_candidates:
                    all_candidates[ticker]['priority'] = 0.9
                    all_candidates[ticker]['source'] = 'news_market'
                else:
                    all_candidates[ticker] = {
                        'reason': info['reason'],
                        'priority': 0.8,
                        'source': 'market',
                        'score': info.get('magnitude', 0.5),
                        'details': info
                    }
            
            # Strategy 3: Portfolio-Driven (Medium Priority - Mandatory)
            self.logger.info("Selecting candidates: Portfolio-Driven...")
            portfolio_candidates = self.portfolio_driver.select_candidates()
            for ticker, info in portfolio_candidates.items():
                if ticker in all_candidates:
                    all_candidates[ticker]['priority'] = max(
                        all_candidates[ticker]['priority'], 0.85
                    )
                else:
                    all_candidates[ticker] = {
                        'reason': info['reason'],
                        'priority': 0.85,  # Mandatory coverage
                        'source': 'portfolio',
                        'score': 1.0,
                        'details': info
                    }
            
            # Strategy 4: Baseline (Lower Priority)
            self.logger.info("Selecting candidates: Baseline...")
            baseline_candidates = self.baseline_rotator.select_candidates(
                rotation_size=baseline_size
            )
            for ticker, info in baseline_candidates.items():
                if ticker not in all_candidates:
                    all_candidates[ticker] = {
                        'reason': info['reason'],
                        'priority': 0.5,
                        'source': 'baseline',
                        'score': 0.5,
                        'details': info
                    }
            
            # Convert to sorted list
            result = [
                (ticker, info['reason'], info['priority'])
                for ticker, info in all_candidates.items()
            ]
            
            # Sort by priority descending, then by ticker
            result.sort(key=lambda x: (-x[2], x[0]))
            
            # Log summary
            self.logger.info(
                f"Candidate selection complete: {len(result)} total candidates",
                extra={
                    'total_candidates': len(result),
                    'news_count': len(news_candidates),
                    'market_count': len(market_candidates),
                    'portfolio_count': len(portfolio_candidates),
                    'baseline_count': len(baseline_candidates),
                }
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Candidate selection failed: {e}")
            raise
    
    def select_candidates_dict(self, **kwargs) -> Dict[str, Dict]:
        """
        Alternative return format: Dict[ticker] -> candidate_info
        """
        candidates_list = self.select_candidates(**kwargs)
        
        # Convert back to dict format for compatibility
        result = {}
        all_candidates = {}
        
        # Get all candidates with full info
        news_candidates = self.news_driver.select_candidates(**kwargs)
        market_candidates = self.market_driver.select_candidates()
        portfolio_candidates = self.portfolio_driver.select_candidates()
        baseline_candidates = self.baseline_rotator.select_candidates()
        
        # Merge all
        for ticker, info in news_candidates.items():
            all_candidates[ticker] = {'source': 'news', **info}
        for ticker, info in market_candidates.items():
            all_candidates[ticker] = {'source': 'market', **info}
        for ticker, info in portfolio_candidates.items():
            all_candidates[ticker] = {'source': 'portfolio', **info}
        for ticker, info in baseline_candidates.items():
            if ticker not in all_candidates:
                all_candidates[ticker] = {'source': 'baseline', **info}
        
        return all_candidates


def select_candidates(hours_lookback: int = 24) -> List[Tuple[str, str, float]]:
    """
    Standalone function to select candidates.
    
    Args:
        hours_lookback: Hours to look back for news
    
    Returns:
        List of (ticker, reason, priority) tuples
    """
    selector = CandidateSelector()
    return selector.select_candidates(hours_lookback=hours_lookback)
