"""
Feature Pipeline - Orchestrates feature engineering

Transforms candidates and market data into ML-ready feature vectors.

Pipeline:
  Candidates → Technical Features → Sentiment Features → Normalization → Feature Vectors
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.features.technical import TechnicalAnalyzer
from src.news.rag import NewsRAG
from src.utils.logging import StructuredLogger, setup_logging
from src.utils.config import load_yaml_config


class FeaturePipeline:
    """Orchestrates feature engineering for ML models."""
    
    # Standard features for XGBoost (order matters!)
    FEATURE_NAMES = [
        'rsi_14', 'rsi_30',
        'sma_20_ratio', 'sma_50_ratio', 'sma_200_ratio',
        'ema_12_ratio', 'ema_26_ratio',
        'macd', 'macd_signal', 'macd_hist',
        'bb_upper_zscore', 'bb_middle_ratio', 'bb_lower_zscore',
        'atr', 'volatility_20d',
        'momentum_3d', 'momentum_5d', 'momentum_10d',
        'volume_ratio', 'volume_zscore',
        'gap_pct', 'intraday_range',
        'sentiment_score', 'sentiment_trend',
        'news_count', 'novelty_score',
        'sector_sentiment',
        'high_low_ratio', 'close_sma20_ratio'
    ]
    
    def __init__(self, logger=None):
        """Initialize feature pipeline."""
        if logger is None:
            config = load_yaml_config('settings')
            logger = StructuredLogger(setup_logging(config.get('logging', {})))
        
        self.logger = logger
        self.technical_analyzer = TechnicalAnalyzer(logger)
        self.news_rag = NewsRAG()
        self.scaler = StandardScaler()
    
    def generate_features(self,
                         candidates: List[str],
                         reference_date: datetime = None,
                         lookback_days: int = 30) -> Dict[str, Dict]:
        """
        Generate features for a list of candidates.
        
        Args:
            candidates: List of ticker symbols
            reference_date: Date to generate features for (default: today)
            lookback_days: Historical lookback period
        
        Returns:
            Dict[ticker] -> {features_dict, feature_vector, quality_score}
        """
        
        results = {}
        
        if reference_date is None:
            reference_date = datetime.utcnow()
        
        try:
            for ticker in candidates:
                try:
                    # Generate technical features
                    tech_features = self.technical_analyzer.analyze(
                        ticker,
                        reference_date=reference_date,
                        lookback_days=lookback_days
                    )
                    
                    # Generate sentiment features
                    sentiment_features = self._get_sentiment_features(
                        ticker,
                        reference_date=reference_date
                    )
                    
                    # Combine all features
                    all_features = {**tech_features, **sentiment_features}
                    
                    # Create feature vector (maintain consistent order)
                    feature_vector = self._to_vector(all_features)
                    
                    # Calculate quality score (% non-NaN features)
                    quality_score = 1.0 - (np.isnan(feature_vector).sum() / len(feature_vector))
                    
                    # Handle NaN values
                    feature_vector = np.nan_to_num(feature_vector, nan=0.0, posinf=0.0, neginf=0.0)
                    
                    results[ticker] = {
                        'features': all_features,
                        'feature_vector': feature_vector,
                        'quality_score': quality_score,
                        'timestamp': reference_date.isoformat(),
                        'nan_count': np.isnan(feature_vector).sum()
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Failed to generate features for {ticker}: {e}")
                    # Create sparse vector on failure
                    results[ticker] = {
                        'features': {},
                        'feature_vector': np.zeros(len(self.FEATURE_NAMES)),
                        'quality_score': 0.0,
                        'error': str(e)
                    }
            
            self.logger.info(
                f"Generated features for {len(results)} candidates",
                extra={'candidate_count': len(results)}
            )
            
        except Exception as e:
            self.logger.error(f"Feature pipeline failed: {e}")
            raise
        
        return results
    
    def _get_sentiment_features(self, ticker: str, reference_date: datetime) -> Dict:
        """Get sentiment features from news RAG."""
        try:
            # Get ticker context from last 24 hours
            context = self.news_rag.get_ticker_context(
                ticker,
                max_hours=24
            )
            
            return {
                'sentiment_score': context.get('avg_sentiment', 0),
                'sentiment_trend': 1 if context.get('sentiment_trend') == 'improving' else 
                                  -1 if context.get('sentiment_trend') == 'deteriorating' else 0,
                'news_count': context.get('count', 0),
                'novelty_score': context.get('novelty', 0),
                'sector_sentiment': context.get('sector_avg_sentiment', 0)
            }
        except Exception as e:
            self.logger.warning(f"Failed to get sentiment features for {ticker}: {e}")
            return {
                'sentiment_score': 0,
                'sentiment_trend': 0,
                'news_count': 0,
                'novelty_score': 0,
                'sector_sentiment': 0
            }
    
    def _to_vector(self, features_dict: Dict) -> np.ndarray:
        """Convert feature dict to ordered numpy array."""
        vector = []
        for feature_name in self.FEATURE_NAMES:
            value = features_dict.get(feature_name, np.nan)
            vector.append(value if isinstance(value, (int, float)) else np.nan)
        return np.array(vector)
    
    def normalize_features(self,
                          feature_vectors: Dict[str, np.ndarray],
                          method: str = 'zscore') -> Dict[str, np.ndarray]:
        """
        Normalize feature vectors.
        
        Args:
            feature_vectors: Dict[ticker] -> feature_vector
            method: 'zscore' or 'minmax'
        
        Returns:
            Dict[ticker] -> normalized_vector
        """
        
        try:
            if not feature_vectors:
                return {}
            
            # Stack vectors for normalization
            vectors = np.array([v for v in feature_vectors.values()])
            
            if method == 'zscore':
                # Z-score normalization (mean=0, std=1)
                normalized = (vectors - vectors.mean(axis=0)) / (vectors.std(axis=0) + 1e-8)
            else:
                # Min-max normalization
                normalized = (vectors - vectors.min(axis=0)) / (vectors.max(axis=0) - vectors.min(axis=0) + 1e-8)
            
            # Handle NaN from division
            normalized = np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)
            
            # Clamp outliers (>3 sigma)
            normalized = np.clip(normalized, -3, 3)
            
            # Create result dict
            result = {}
            tickers = list(feature_vectors.keys())
            for i, ticker in enumerate(tickers):
                result[ticker] = normalized[i]
            
            self.logger.info(
                f"Normalized {len(result)} feature vectors using {method}",
                extra={'method': method, 'count': len(result)}
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Normalization failed: {e}")
            # Return original on failure
            return feature_vectors


def generate_features(candidates: List[str]) -> Dict[str, Dict]:
    """
    Standalone function to generate features for candidates.
    
    Args:
        candidates: List of ticker symbols
    
    Returns:
        Dict[ticker] -> feature_vectors and metadata
    """
    pipeline = FeaturePipeline()
    return pipeline.generate_features(candidates)
