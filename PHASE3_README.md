# Phase 3: Candidates Selection & Feature Engineering

**Status:** 🚀 IN PROGRESS  
**Started:** February 3, 2026  
**Previous Phase:** ✅ [Phase 2 Complete](PHASE2_COMPLETE.md) - News pipeline operational

---

## 🎯 Phase 3 Objectives

Build the **candidate selection engine** and **feature engineering pipeline** that transforms news sentiment and market data into ML-ready feature vectors.

### Key Deliverables

1. ✅ Candidates Selector - Orchestrates 4 selection strategies
2. ✅ News-Driven Selection - High sentiment + novelty articles
3. ✅ Market-Driven Selection - Gaps, volume, volatility anomalies
4. ✅ Portfolio-Driven Selection - Mandatory open position coverage
5. ✅ Baseline Rotation - Blue-chip stock coverage
6. ✅ Feature Engineering Pipeline - Create ML-ready vectors
7. ✅ Comprehensive Testing & Validation

---

## 📋 Component Overview

### Data Flow: Phase 2 → Phase 3

```
Phase 2 (News Pipeline)          Phase 3 (Candidates & Features)
═════════════════════════════════════════════════════════════════

News Articles          →    Candidate Selection
├─ Sentiment Score          ├─ News-Driven (high sentiment)
├─ Novelty Score           ├─ Market-Driven (gaps/volume)
├─ Ticker Tags             ├─ Portfolio-Driven (open positions)
└─ Embeddings              └─ Baseline (rotation)
                                    ↓
OHLCV Data             →    Feature Engineering
├─ Daily prices             ├─ Technical indicators
├─ Volume               ├─ Sentiment aggregation
└─ Volatility               └─ Normalization/Scaling
                                    ↓
                           Feature Store
                           ├─ ticker, date, feature_vector
                           └─ Ready for ML inference

```

---

## 🏗️ Architecture: Candidate Selection

### 1. News-Driven Selection
**Module:** `src/candidates/news_driven.py`

Selects candidates based on news sentiment and novelty:
- High positive sentiment (>0.5) → Consider BUY
- High negative sentiment (<-0.5) → Consider SELL
- High novelty (>0.8) → Event-driven opportunity
- Filters: Last 24 hours, unique tickers

**Output:**
```python
{
    "AAPL": {"reason": "earnings_positive", "sentiment": 0.87, "novelty": 0.92},
    "TSLA": {"reason": "negative_event", "sentiment": -0.73, "novelty": 0.85},
}
```

### 2. Market-Driven Selection
**Module:** `src/candidates/market_driven.py`

Selects candidates based on technical/market anomalies:
- Large gaps (>1%) from previous close
- Abnormal volume (>2 std dev)
- Volatility spikes (>1.5x average)
- Breakouts/breakdowns (crossing key levels)
- Filters: Last trading day

**Output:**
```python
{
    "SPY": {"reason": "large_gap", "gap_pct": 1.25, "magnitude": "high"},
    "QQQ": {"reason": "volume_spike", "volume_zscore": 2.3, "magnitude": "medium"},
}
```

### 3. Portfolio-Driven Selection
**Module:** `src/candidates/portfolio_driven.py`

Mandatory coverage of all open positions:
- All open positions (100% coverage)
- Positions near stop loss (-2% from entry)
- Positions near take-profit target (+3% from entry)
- Positions with deteriorating technicals

**Output:**
```python
{
    "MSFT": {"reason": "open_position", "entry": 375.25, "current": 378.50},
    "NVDA": {"reason": "approaching_tp", "target": 145.00, "current": 143.25},
}
```

### 4. Baseline Rotation
**Module:** `src/candidates/baseline.py`

Rotating coverage to avoid blind spots:
- Blue-chip stock universe (50-100 stocks)
- Daily rotation (5-10% of universe per day)
- Ensures no major movers missed
- Coverage cycle: 10-20 days

**Output:**
```python
{
    "JPM": {"reason": "baseline_rotation", "day_in_cycle": 1},
    "XOM": {"reason": "baseline_rotation", "day_in_cycle": 2},
}
```

### 5. Candidates Selector (Orchestrator)
**Module:** `src/candidates/selector.py`

Combines all 4 strategies:
- De-duplication (union of all strategies)
- Priority scoring (news > market > portfolio > baseline)
- Ranking by signal strength
- Returns final candidate list for analysis

**Output:**
```python
[
    ("AAPL", "news_sentiment", 0.87),
    ("TSLA", "news_sentiment", -0.73),
    ("SPY", "market_gap", 1.25),
    ("MSFT", "portfolio", 0.75),
    ("JPM", "baseline", 0.50),
]
```

---

## 🔧 Feature Engineering Pipeline

### Architecture: Features → ML Input

**Module:** `src/features/pipeline.py`

Transforms raw candidates and market data into ML-ready vectors:

#### Input
```python
{
    "timestamp": "2024-01-16T10:00:00Z",
    "candidates": ["AAPL", "MSFT", "TSLA", "JPM", "XOM"],
    "lookback_days": 30
}
```

#### Processing Steps

1. **Technical Features** (src/features/technical.py)
   - 14-day RSI (momentum)
   - 20-day SMA, 50-day SMA (trend)
   - Bollinger Bands (volatility)
   - MACD (momentum)
   - ATR (volatility)
   - Volume trend (ratio to 20-day avg)

2. **News Sentiment Features** (src/news/rag.py)
   - Avg sentiment (last 24h)
   - Sentiment trend (deteriorating/stable/improving)
   - News count (urgency)
   - Novelty score (event-driven)
   - Sector sentiment (context)

3. **Market Features** (from OHLCV data)
   - Gap % (open-close)
   - Intraday range (high-low)
   - Volume ratio (vs 20-day avg)
   - Price momentum (3-day, 5-day)
   - Volatility (20-day historical)

4. **Normalization/Scaling**
   - Z-score normalization (mean=0, std=1)
   - Handles missing data (forward fill, then interpolate)
   - Removes outliers (>3σ clamped)

#### Output
```python
{
    "timestamp": "2024-01-16T10:00:00Z",
    "features": {
        "AAPL": {
            "rsi_14": 0.65,
            "sma_20_ratio": 1.012,
            "sentiment_score": 0.87,
            "sentiment_trend": 1,
            "news_count": 5,
            "novelty_score": 0.92,
            "volume_zscore": 1.3,
            "gap_pct": 0.25,
            "momentum_3d": 0.018,
            "volatility_20d": 0.015,
            # ... more features
        },
        "MSFT": { ... },
        # ... remaining candidates
    }
}
```

#### Feature Vector Format (for ML)
```python
# Ordered feature array [30 features]
feature_vector = [
    0.65,   # RSI_14
    1.012,  # SMA_20_ratio
    0.75,   # SMA_50_ratio
    1.25,   # Bollinger upper zscore
    0.18,   # MACD
    12.5,   # ATR
    1.3,    # Volume ratio
    0.87,   # Sentiment score
    1,      # Sentiment trend
    5,      # News count (normalized)
    0.92,   # Novelty score
    0.25,   # Gap %
    0.018,  # Momentum 3d
    0.015,  # Volatility 20d
    # ... 16 more features
]
```

---

## 🗂️ Directory Structure

```
src/
├── candidates/
│   ├── __init__.py
│   ├── selector.py           # Main orchestrator
│   ├── news_driven.py        # News-based selection
│   ├── market_driven.py      # Technical-based selection
│   ├── portfolio_driven.py   # Portfolio-based selection
│   └── baseline.py           # Baseline rotation
├── features/
│   ├── __init__.py
│   ├── pipeline.py           # Feature engineering pipeline
│   ├── technical.py          # Technical indicator calculations
│   ├── sentiment.py          # Sentiment aggregation
│   └── store.py              # Feature store (existing)
└── ... (other modules)
```

---

## 🚀 Implementation Plan

### Phase 3A: Candidate Selection (Days 1-3)
1. News-Driven Selector
2. Market-Driven Selector  
3. Portfolio-Driven Selector
4. Baseline Selector
5. Main Orchestrator

### Phase 3B: Feature Engineering (Days 4-6)
1. Technical indicator calculations
2. Sentiment aggregation
3. Market feature extraction
4. Normalization & scaling
5. Feature store integration

### Phase 3C: Testing & Validation (Day 7)
1. Unit tests for each component
2. Integration tests (full pipeline)
3. End-to-end validation with real data
4. Performance benchmarking
5. Documentation

---

## 📊 Success Criteria

- ✅ Candidates selector produces 20-50 candidates per run
- ✅ Feature pipeline generates 30+ features per candidate
- ✅ All features properly normalized (mean≈0, std≈1)
- ✅ No missing data in feature vectors (handled gracefully)
- ✅ Feature vectors in correct format for XGBoost
- ✅ Comprehensive test coverage (unit + integration)
- ✅ Pipeline runs in <5 seconds for 50 candidates
- ✅ All components documented with examples

---

## 🔗 Dependencies

### From Phase 2 (Already Available)
- `src/news/rag.py` - Retrieve news context by ticker
- `src/news/storage.py` - Query stored news articles
- `src/news/embedder.py` - Semantic similarity (future use)

### New Dependencies
- `yfinance` - Download OHLCV data (fallback)
- `Alpaca` - Market data API (primary)
- `pandas_ta` - Technical indicators
- Existing: `pandas`, `numpy`, `sqlalchemy`

### Data Sources
- **News:** PostgreSQL (Phase 2 output)
- **OHLCV:** Alpaca API (primary), Yahoo Finance (fallback)
- **Portfolio:** Alpaca paper trading account
- **Calendar:** Holiday/trading hours helpers

---

## 🧪 Testing Strategy

### Unit Tests
- Each selector returns correct format
- Features properly calculated
- Normalization works correctly
- Error handling (missing data, API failures)

### Integration Tests
- Full pipeline: candidates → features → ready for ML
- With real market data
- With sample news articles
- Performance under load

### Validation Script
- `scripts/tests/test_candidates_features.py`
- End-to-end pipeline test
- Produce sample feature vectors
- Generate statistical reports

---

## 📈 Metrics & Monitoring

### Candidate Selection Metrics
- Number of candidates selected per run
- Distribution by source (news/market/portfolio/baseline)
- Unique candidates (de-duplication ratio)
- Average signal strength

### Feature Quality Metrics
- Feature completeness (% non-NaN)
- Normalization verification (mean, std dev)
- Feature correlation matrix
- Outlier detection

### Performance Metrics
- Selector execution time
- Feature engineering time
- Total pipeline time
- Memory usage

---

## 🎯 Next Steps After Phase 3

Once Phase 3 is complete:
- **Phase 4:** ML Training - XGBoost model with engineered features
- **Phase 5:** Agent Ensemble - Bull/Bear/Risk committee
- **Phase 6:** Execution Engine - Alpaca order placement
- **Phase 7:** Scheduler - Automated twice-daily runs

---

## 📚 References

- [DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md) - Candidate selection policy
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Data flow diagrams
- [API_CONTRACTS.md](docs/API_CONTRACTS.md) - Component interfaces
- [PHASE2_COMPLETE.md](PHASE2_COMPLETE.md) - News pipeline details

---

**Last Updated:** February 3, 2026  
**Phase Status:** 🚀 IN PROGRESS  
**Next Milestone:** Complete Candidates Selector & Feature Pipeline
