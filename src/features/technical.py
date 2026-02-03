"""
Technical Indicators Module

Computes technical indicators for feature engineering.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


class TechnicalAnalyzer:
    """Compute technical indicators from OHLCV data."""
    
    def __init__(self, logger=None):
        """Initialize technical analyzer."""
        if logger is None:
            config = load_yaml_config('settings')
            logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        self.logger = logger
    
    def analyze(self,
               ticker: str,
               reference_date: datetime = None,
               lookback_days: int = 30) -> Dict:
        """
        Compute all technical indicators for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            reference_date: Date to analyze (default: today)
            lookback_days: Historical lookback period
        
        Returns:
            Dict of computed indicators
        
        Note: This is a Phase 4 enhancement that requires OHLCV data.
              For now, returns placeholder values.
        """
        
        indicators = {
            # RSI indicators
            'rsi_14': np.nan,
            'rsi_30': np.nan,
            
            # Moving averages
            'sma_20_ratio': np.nan,
            'sma_50_ratio': np.nan,
            'sma_200_ratio': np.nan,
            'ema_12_ratio': np.nan,
            'ema_26_ratio': np.nan,
            
            # MACD
            'macd': np.nan,
            'macd_signal': np.nan,
            'macd_hist': np.nan,
            
            # Bollinger Bands
            'bb_upper_zscore': np.nan,
            'bb_middle_ratio': np.nan,
            'bb_lower_zscore': np.nan,
            
            # ATR and Volatility
            'atr': np.nan,
            'volatility_20d': np.nan,
            
            # Momentum
            'momentum_3d': np.nan,
            'momentum_5d': np.nan,
            'momentum_10d': np.nan,
            
            # Volume
            'volume_ratio': np.nan,
            'volume_zscore': np.nan,
            
            # Gap and Range
            'gap_pct': np.nan,
            'intraday_range': np.nan,
            'high_low_ratio': np.nan,
            'close_sma20_ratio': np.nan,
        }
        
        try:
            # TODO: Phase 4 enhancement
            # This requires fetching OHLCV data from Alpaca or Yahoo Finance
            # Implementation will:
            # 1. Query database for historical OHLCV
            # 2. Compute each indicator using pandas/numpy
            # 3. Return normalized ratios
            
            self.logger.info(
                f"Technical analysis for {ticker}: requires OHLCV data (Phase 4)",
                extra={'ticker': ticker, 'status': 'deferred'}
            )
            
        except Exception as e:
            self.logger.warning(f"Technical analysis failed for {ticker}: {e}")
        
        return indicators
    
    @staticmethod
    def compute_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Compute Relative Strength Index."""
        if len(prices) < period + 1:
            return np.full_like(prices, np.nan)
        
        deltas = np.diff(prices)
        ups = np.where(deltas > 0, deltas, 0)
        downs = np.where(deltas < 0, -deltas, 0)
        
        avg_up = pd.Series(ups).rolling(window=period).mean().values
        avg_down = pd.Series(downs).rolling(window=period).mean().values
        
        rs = avg_up / (avg_down + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi / 100.0  # Normalize to 0-1
    
    @staticmethod
    def compute_macd(prices: np.ndarray, 
                     fast: int = 12, 
                     slow: int = 26, 
                     signal: int = 9) -> tuple:
        """Compute MACD indicator."""
        if len(prices) < slow + signal:
            return np.full_like(prices, np.nan), np.full_like(prices, np.nan), np.full_like(prices, np.nan)
        
        prices_series = pd.Series(prices)
        
        ema_fast = prices_series.ewm(span=fast).mean().values
        ema_slow = prices_series.ewm(span=slow).mean().values
        
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=signal).mean().values
        macd_hist = macd_line - signal_line
        
        return macd_line, signal_line, macd_hist
    
    @staticmethod
    def compute_bollinger_bands(prices: np.ndarray, 
                               period: int = 20, 
                               std_dev: float = 2) -> tuple:
        """Compute Bollinger Bands."""
        if len(prices) < period:
            return np.full_like(prices, np.nan), np.full_like(prices, np.nan), np.full_like(prices, np.nan)
        
        prices_series = pd.Series(prices)
        sma = prices_series.rolling(window=period).mean().values
        std = prices_series.rolling(window=period).std().values
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return upper, sma, lower
    
    @staticmethod
    def compute_momentum(prices: np.ndarray, period: int = 5) -> np.ndarray:
        """Compute momentum (percentage change)."""
        if len(prices) < period + 1:
            return np.full_like(prices, np.nan)
        
        momentum = (prices - np.roll(prices, period)) / np.roll(prices, period)
        return momentum
    
    @staticmethod
    def compute_atr(high: np.ndarray, 
                    low: np.ndarray, 
                    close: np.ndarray, 
                    period: int = 14) -> np.ndarray:
        """Compute Average True Range."""
        if len(high) < period:
            return np.full_like(close, np.nan)
        
        tr1 = high - low
        tr2 = np.abs(high - np.roll(close, 1))
        tr3 = np.abs(low - np.roll(close, 1))
        
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = pd.Series(tr).rolling(window=period).mean().values
        
        return atr / close  # Normalize
