"""
Baseline Candidate Rotation

Rotating coverage of blue-chip stocks to prevent blind spots.
Daily rotation ensures no major mover is missed.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


# S&P 100 Blue Chip universe (core holding liquid stocks)
BASELINE_UNIVERSE = [
    # Tech Giants (10)
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA',
    'META', 'TSLA', 'NFLX', 'CRM', 'ADBE',
    
    # Finance (8)
    'JPM', 'BAC', 'WFC', 'GS', 'MS',
    'BLK', 'SCHW', 'AXP',
    
    # Healthcare (7)
    'PFE', 'JNJ', 'UNH', 'MRK', 'ABBV',
    'LLY', 'BMY',
    
    # Industrials (6)
    'BA', 'CAT', 'GE', 'LMT', 'RTX', 'HON',
    
    # Energy (4)
    'XOM', 'CVX', 'COP', 'SLB',
    
    # Consumer (7)
    'WMT', 'KO', 'MCD', 'NKE', 'COST', 'TJX', 'HD',
    
    # Communications (3)
    'VZ', 'T', 'CMCSA',
    
    # Utilities (3)
    'NEE', 'D', 'SO',
    
    # Diversified (4)
    'BRK.B', 'PM', 'MO', 'MMM',
    
    # Real Estate (3)
    'PLD', 'SPG', 'O',
    
    # Transportation (2)
    'FDX', 'UPS',
]


class BaselineRotator:
    """Rotate coverage through blue-chip universe."""
    
    def __init__(self, logger=None):
        """Initialize baseline rotator."""
        if logger is None:
            config = load_yaml_config('settings')
            logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        self.logger = logger
        self.universe = BASELINE_UNIVERSE
    
    def select_candidates(self,
                         rotation_size: int = 10,
                         reference_date: datetime = None) -> Dict[str, Dict]:
        """
        Select baseline candidates using rotating schedule.
        
        Args:
            rotation_size: Number of candidates per day (default: 10)
            reference_date: Date to calculate rotation for (default: today)
        
        Returns:
            Dict[ticker] -> {reason, day_in_cycle, rotation_index}
        """
        
        candidates = {}
        
        try:
            if reference_date is None:
                reference_date = datetime.utcnow()
            
            # Calculate which part of rotation we're in
            # Use day of year to determine rotation offset
            day_of_year = reference_date.timetuple().tm_yday
            rotation_offset = day_of_year % len(self.universe)
            
            # Select rotation_size candidates
            selected = []
            for i in range(rotation_size):
                idx = (rotation_offset + i) % len(self.universe)
                ticker = self.universe[idx]
                selected.append((ticker, idx))
            
            # Build candidate dict
            for ticker, idx in selected:
                candidates[ticker] = {
                    'reason': 'baseline_rotation',
                    'day_in_cycle': idx % rotation_size,
                    'rotation_index': idx,
                    'priority': 0.5  # Lower priority than news/market
                }
            
            cycle_length = len(self.universe) // rotation_size
            self.logger.info(
                f"Baseline rotation: {len(candidates)} candidates from universe of {len(self.universe)}",
                extra={
                    'candidate_count': len(candidates),
                    'universe_size': len(self.universe),
                    'cycle_length_days': cycle_length
                }
            )
            
        except Exception as e:
            self.logger.error(f"Baseline selection failed: {e}")
            raise
        
        return candidates


def get_baseline_candidates(rotation_size: int = 10) -> Dict[str, Dict]:
    """
    Standalone function to get baseline candidates.
    
    Args:
        rotation_size: Number of candidates to select per day
    
    Returns:
        Dict of candidates from baseline rotation
    """
    rotator = BaselineRotator()
    return rotator.select_candidates(rotation_size=rotation_size)
