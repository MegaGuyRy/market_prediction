# API Contracts – Component Communication

**Purpose:** Define the exact data structures and contracts between components.  
**Status:** Design phase – implement as specified during each phase.

---

## 1. Candidate Selector → ML

**Input:** List of tickers to analyze

```json
{
  "timestamp": "2024-01-16T10:00:00Z",
  "candidates": [
    {
      "ticker": "AAPL",
      "reason": "earnings_announcement",
      "signal_strength": "high",
      "news_context": "Apple Q4 earnings beat estimates"
    },
    {
      "ticker": "MSFT",
      "reason": "large_gap",
      "signal_strength": "medium",
      "gap_pct": 2.3
    }
  ]
}
```

**Output:** Dictionary of signals (keyed by ticker)

---

## 2. ML Inference Engine Output

**Output:** Signal with confidence and edge score

```json
{
  "timestamp": "2024-01-16T10:15:00Z",
  "signals": {
    "AAPL": {
      "signal": "BUY",
      "confidence": 0.87,
      "expected_return_pct": 2.3,
      "edge_score": 0.72,
      "reasoning": "Strong momentum + positive sentiment + technical setup"
    },
    "MSFT": {
      "signal": "HOLD",
      "confidence": 0.65,
      "expected_return_pct": 0.1,
      "edge_score": 0.52,
      "reasoning": "Gap filled, waiting for confirmation"
    }
  }
}
```

**Valid Signals:** `BUY`, `SELL`, `HOLD`

---

## 3. ML → Agent System

**Input:** Proposal (only BUY/SELL, not HOLD)

```json
{
  "timestamp": "2024-01-16T10:15:00Z",
  "proposal": {
    "ticker": "AAPL",
    "signal": "BUY",
    "ml_confidence": 0.87,
    "expected_return_pct": 2.3,
    "edge_score": 0.72,
    "rationale": "XGBoost signal + positive sentiment + momentum alignment"
  },
  "news_context": [
    {
      "title": "Apple Q4 Earnings Beat Expectations",
      "source": "Reuters",
      "timestamp": "2024-01-15T16:30:00Z",
      "sentiment": "positive"
    }
  ]
}
```

---

## 4. Agent → Committee

Each agent responds with structured JSON:

```json
{
  "agent": "analyst",
  "timestamp": "2024-01-16T10:20:00Z",
  "ticker": "AAPL",
  "assessment": {
    "regime": "post-earnings bounce",
    "anomalies": ["unusual volume spike"],
    "confidence": 0.80
  },
  "recommendation": "APPROVE",
  "reasoning": "Earnings catalyst + technical confirmation"
}
```

**Agent Types & Fields:**

### Market Analyst
```json
{
  "agent": "analyst",
  "assessment": {
    "regime": "string (bull/bear/sideways/post_event)",
    "anomalies": ["string"],
    "technical_setup": "string"
  },
  "recommendation": "APPROVE | VETO | REDUCE",
  "reasoning": "string"
}
```

### Bull Agent
```json
{
  "agent": "bull",
  "best_case": {
    "return_target_pct": 5.0,
    "catalysts": ["earnings strength", "analyst upgrade"]
  },
  "recommendation": "APPROVE | VETO | REDUCE",
  "reasoning": "string"
}
```

### Bear Agent
```json
{
  "agent": "bear",
  "risks": [
    {
      "risk": "valuation stretched",
      "likelihood": "medium",
      "impact": "high"
    }
  ],
  "recommendation": "APPROVE | VETO | REDUCE",
  "reasoning": "string"
}
```

### Risk Manager
```json
{
  "agent": "risk",
  "exposure_analysis": {
    "sector": "technology",
    "current_tech_exposure_pct": 35,
    "new_exposure_if_approved_pct": 40
  },
  "event_risks": ["earnings volatility"],
  "recommendation": "APPROVE | VETO | REDUCE",
  "reasoning": "string"
}
```

### Committee (Synthesis)
```json
{
  "agent": "committee",
  "summary": {
    "approvals": 3,
    "vetoes": 1,
    "reduces": 0
  },
  "final_recommendation": "APPROVE | VETO | REDUCE",
  "reasoning": "Analyst + Bull + Risk unanimous. Bear flags valuation, but earnings support overweighs concern."
}
```

---

## 5. Agent System → Risk Controller

**Input:** Committee recommendation

```json
{
  "timestamp": "2024-01-16T10:25:00Z",
  "ml_proposal": {
    "ticker": "AAPL",
    "signal": "BUY",
    "confidence": 0.87,
    "expected_return_pct": 2.3
  },
  "agent_recommendation": "APPROVE",
  "agent_summary": "Analyst + Bull support. Bear concern on valuation noted but earnings outweigh.",
  "entry_price": 185.50
}
```

---

## 6. Risk Controller Output → Execution

**Output:** Sized order ready for execution

```json
{
  "timestamp": "2024-01-16T10:30:00Z",
  "order": {
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 50,
    "order_type": "MARKET",
    "stop_loss_price": 182.00,
    "target_price": 189.00,
    "max_loss_usd": 175.00,
    "rationale": "0.5% risk sizing, 50 shares at $185.50 entry"
  },
  "position_limits_check": {
    "current_positions": 8,
    "max_allowed": 15,
    "single_stock_exposure_pct": 3.2,
    "max_single_stock_pct": 10.0,
    "total_portfolio_exposure_pct": 85,
    "all_constraints_passed": true
  }
}
```

---

## 7. Execution Engine → Trade Log

**Output:** Filled trade record

```json
{
  "timestamp": "2024-01-16T10:35:00Z",
  "trade": {
    "trade_id": "trade_20240116_001",
    "ticker": "AAPL",
    "action": "BUY",
    "quantity": 50,
    "fill_price": 185.52,
    "fill_time": "2024-01-16T10:35:23Z",
    "order_id": "alpaca_12345",
    "commissions": 0.0,
    "total_cost": 9276.00,
    "stop_loss": 182.00,
    "target": 189.00
  }
}
```

---

## 8. Audit Log Entry

**Every decision step logged:**

```json
{
  "event_id": "event_20240116_001",
  "timestamp": "2024-01-16T10:00:00Z",
  "event_type": "signal_generated | agent_critique | risk_approval | order_submitted | fill_confirmed | drawdown_triggered",
  "component": "ml | agents | risk | execution",
  "ticker": "AAPL",
  "data": {
    "signal": "BUY",
    "confidence": 0.87,
    "committee_recommendation": "APPROVE",
    "risk_verdict": "APPROVED",
    "fill_price": 185.52
  },
  "audit_trail_id": "trade_20240116_001"
}
```

---

## 9. Portfolio State (Persistence)

**Stored in PostgreSQL, queried by orchestrator & intraday monitor:**

```json
{
  "timestamp": "2024-01-16T10:35:00Z",
  "account": {
    "total_value_usd": 100000,
    "cash_usd": 9724,
    "positions_value_usd": 90276,
    "unrealized_pnl_usd": 1500,
    "unrealized_pnl_pct": 1.5,
    "daily_drawdown_pct": 0.5,
    "max_daily_drawdown_pct": 1.2
  },
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 50,
      "entry_price": 185.52,
      "current_price": 186.00,
      "unrealized_pnl_usd": 24,
      "unrealized_pnl_pct": 0.13,
      "stop_loss": 182.00,
      "target": 189.00
    }
  ],
  "constraints_status": {
    "max_positions": { "current": 1, "max": 15, "violated": false },
    "max_exposure_pct": { "current": 85, "max": 100, "violated": false },
    "max_daily_drawdown_pct": { "current": 1.2, "hard_limit": 3, "soft_limit": 2, "soft_limit_triggered": false }
  }
}
```

---

## 10. Intraday Stop Enforcement

**Real-time monitoring (no agents):**

```json
{
  "timestamp": "2024-01-16T11:30:00Z",
  "monitor_type": "intraday_enforcement",
  "checks": [
    {
      "ticker": "AAPL",
      "current_price": 181.50,
      "stop_loss": 182.00,
      "status": "STOP_TRIGGERED",
      "action": "SELL"
    }
  ],
  "portfolio_drawdown_pct": 3.1,
  "drawdown_status": "HARD_LIMIT_TRIGGERED",
  "action": "REDUCE_ALL_POSITIONS_BY_50_PCT"
}
```

---

## 11. Feature Store Query

**Features used by ML model:**

```json
{
  "ticker": "AAPL",
  "date": "2024-01-16",
  "ohlcv": {
    "open": 185.00,
    "high": 186.50,
    "low": 184.50,
    "close": 185.90,
    "volume": 45000000
  },
  "technical": {
    "rsi": 65.2,
    "macd": 1.2,
    "bb_upper": 188.00,
    "bb_lower": 183.00,
    "momentum_5d": 2.1
  },
  "sentiment": {
    "news_sentiment": 0.72,
    "sentiment_sources": 3,
    "sentiment_novelty": 0.85
  }
}
```

---

## 12. Model Training Input

**Feature matrix for XGBoost:**

```json
{
  "training_data": {
    "features": [
      {
        "ticker": "AAPL",
        "date": "2024-01-16",
        "features": [/* ohlcv + technical + sentiment */],
        "target": 1
      }
    ],
    "date_range": "2022-01-01 to 2024-01-15",
    "train_test_split": 0.8,
    "target_definition": "1D forward return > 0 = 1, else 0"
  }
}
```

---

## Summary Table

| From | To | Format |
|------|-----|--------|
| Candidates | ML | List of tickers + context |
| ML | Agents | BUY/SELL proposal + confidence |
| Agents | Committee | Structured critique JSON |
| Committee | Risk | Recommendation (APPROVE/VETO/REDUCE) |
| Risk | Execution | Sized order with stops/targets |
| Execution | Audit Log | Filled trade record |
| Intraday Monitor | Control | Stop triggers, drawdown enforcement |

---

## Notes

1. **All timestamps are ISO 8601 UTC**
2. **All prices in USD**
3. **All percentages are decimals (87% = 0.87)**
4. **All JSON responses validated before use**
5. **Any parsing failure → retry or skip with audit log**

