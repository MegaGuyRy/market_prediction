# System Architecture – Detailed View

**Purpose:** Visual and detailed reference of system components, data flows, and dependencies.

---

## High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                             │
│                 (scheduler/orchestrator.py)                     │
│          Twice daily: 9:35 AM ET, 3:45 PM ET (pre-close)       │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
┌───────────────────┐ ┌─────────────────┐ ┌──────────────────┐
│  NEWS INGESTION   │ │ MARKET DATA     │ │  PORTFOLIO STATE │
│                   │ │                 │ │                  │
│ • RSS fetchers    │ │ • Alpaca OHLCV  │ │ • Current        │
│ • Parse & embed   │ │ • Yahoo backup  │ │   positions      │
│ • pgvector store  │ │ • Normalize     │ │ • Cash balance   │
│ • RAG retrieval   │ │                 │ │ • PnL tracking   │
└────────┬──────────┘ └────────┬────────┘ └────────┬─────────┘
         │                     │                    │
         └─────────────────────┼────────────────────┘
                               ↓
              ┌────────────────────────────────┐
              │  CANDIDATE SELECTOR            │
              │ (candidates/selector.py)       │
              │                                │
              │ Inputs:                        │
              │  • News (embeddings + scores)  │
              │  • Market moves (gaps, vol)    │
              │  • Open positions              │
              │  • Universe (S&P 100-150)      │
              │                                │
              │ Output: List of tickers to     │
              │         analyze (candidates)   │
              └────────┬─────────────────────┘
                       ↓
         ┌─────────────────────────────────┐
         │  FEATURE ENGINEERING            │
         │ (features/pipeline.py)          │
         │                                 │
         │ • Load OHLCV from DB            │
         │ • Compute technical             │
         │   (RSI, MACD, momentum, etc)    │
         │ • Sentiment scores              │
         │ • Scale & align                 │
         │                                 │
         │ Output: Feature vectors for ML  │
         └────────┬────────────────────────┘
                  ↓
         ┌────────────────────────┐
         │  ML SIGNAL ENGINE      │
         │ (ml/inference.py)      │
         │                        │
         │ Model: XGBoost         │
         │ Input: Features        │
         │ Output: Signal         │
         │         Confidence     │
         │         Expected ret   │
         │         Edge score     │
         │                        │
         │ → Only BUY/SELL        │
         │   (HOLD skips agents)  │
         └────────┬───────────────┘
                  ↓
         ┌────────────────────────┐
         │  AGENT CRITIQUE        │
         │ (agents/committee.py)  │
         │                        │
         │ • Analyst (regime)     │
         │ • Bull (thesis)        │
         │ • Bear (risks)         │
         │ • Risk (exposure)      │
         │ • Committee (final)    │
         │                        │
         │ Output:                │
         │   APPROVE/VETO/REDUCE  │
         │   JSON + rationale     │
         └────────┬───────────────┘
                  ↓
         ┌────────────────────────┐
         │  RISK CONTROLLER       │
         │ (risk/controller.py)   │
         │                        │
         │ • Sizing (0.5% risk)   │
         │ • Constraints          │
         │   - Max 15 positions   │
         │   - Max 10% single     │
         │   - Max 100% exposure  │
         │ • Stops/targets        │
         │ • Drawdown check       │
         │                        │
         │ Output: Sized order    │
         │         (or REJECT)    │
         └────────┬───────────────┘
                  ↓
         ┌────────────────────────┐
         │  EXECUTION ENGINE      │
         │ (execution/client.py)  │
         │                        │
         │ • Alpaca API (paper)   │
         │ • Submit orders        │
         │ • Track fills          │
         │ • Record trades        │
         │                        │
         │ Output: Trade records  │
         │         in DB          │
         └────────┬───────────────┘
                  ↓
         ┌────────────────────────┐
         │  AUDIT LOGGING         │
         │ (utils/logging.py)     │
         │                        │
         │ • Every step logged    │
         │ • JSON + PostgreSQL    │
         │ • Queryable trail      │
         └────────────────────────┘


        INTRADAY MONITORING (Continuous, No Agents)
        ──────────────────────────────────────────
        
            ┌─────────────────────────┐
            │  INTRADAY MONITOR       │
            │ (scheduler/intraday.py) │
            │                         │
            │ Every 15-30 minutes:    │
            │ • Fetch market prices   │
            │ • Check stops           │
            │ • Check drawdown        │
            │ • Emergency rules       │
            │                         │
            │ Actions (deterministic)│
            │ • Stop-loss execution   │
            │ • Drawdown de-risk      │
            │ • Gap/volatility rules  │
            └────────┬────────────────┘
                     ↓
            ┌────────────────────────┐
            │  EMERGENCY EXECUTION   │
            │ (execution/client.py)  │
            │                        │
            │ • Market stop orders   │
            │ • Position reduction   │
            │ • Trading halt if >3%DD│
            └────────────────────────┘
```

---

## Data Flow: Single Decision (Morning Run Example)

**Time: 9:35 AM ET**

```
1. NEWS INGESTION (9:30 AM – 9:35 AM)
   ├─ Fetch RSS feeds (overnight news, premarket)
   ├─ Parse: earnings announcements, M&A, legal events
   ├─ Embed with LLM + store in pgvector
   └─ Score sentiment: positive/negative/neutral

2. CANDIDATE SELECTION (9:35 AM)
   ├─ News-driven: Earnings? M&A? Legal? Analyst downgrade?
   │   → AAPL, MSFT, TSLA, GOOGL (high novelty)
   │
   ├─ Market-driven: Gaps? Volume spikes? Volatility?
   │   → SPY gap up 2%, NVDA 15% volume spike
   │
   ├─ Portfolio-driven: Current positions near stops?
   │   → JPM (in portfolio, near target), KO (near stop)
   │
   ├─ Baseline rotation: Haven't analyzed XOM, JNJ in 7 days?
   │   → Add to candidate pool
   │
   └─ Final candidate pool: [AAPL, MSFT, TSLA, GOOGL, SPY, NVDA, JPM, KO, XOM, JNJ]
       (10 tickers for analysis)

3. MARKET DATA FETCH (9:35 AM)
   ├─ Alpaca: last 20 days OHLCV for candidates
   ├─ Yahoo backup: if Alpaca delayed
   ├─ Store in PostgreSQL
   └─ Verify data quality (no gaps, splits)

4. FEATURE ENGINEERING (9:36 AM)
   ├─ For each candidate:
   │   ├─ Load OHLCV from DB
   │   ├─ Compute RSI, MACD, Bollinger Bands, momentum
   │   ├─ Get news sentiment (via RAG query)
   │   ├─ Scale features (normalize to XGBoost input)
   │   └─ Store feature vector in feature store
   └─ Ready for ML inference

5. ML INFERENCE (9:37 AM)
   ├─ Load trained XGBoost model
   ├─ For each candidate, run inference:
   │   ├─ AAPL → BUY (confidence 0.87, expected return +2.3%)
   │   ├─ MSFT → HOLD (confidence 0.65, skip agents)
   │   ├─ TSLA → SELL (confidence 0.79, expected return -1.5%)
   │   ├─ [... remaining tickers ...]
   │   └─ Store signals in DB
   └─ Proposals ready: [AAPL BUY, TSLA SELL, ...]

6. AGENT CRITIQUE (9:38 AM – 9:43 AM, ~1 min per BUY/SELL)
   ├─ For AAPL BUY proposal:
   │   ├─ Analyst: "Post-earnings momentum, tech sector bullish" → APPROVE
   │   ├─ Bull: "Earnings beat, guidance up, multiple expansion" → APPROVE
   │   ├─ Bear: "Valuation high, consumer slowdown risk" → REDUCE
   │   ├─ Risk: "Tech exposure 35%, adding 5% more OK, but watch sector" → APPROVE
   │   └─ Committee: 3 APPROVE, 1 REDUCE → Recommendation: APPROVE
   │
   ├─ For TSLA SELL proposal:
   │   ├─ Analyst: "Margin compression, China demand weak" → APPROVE
   │   ├─ Bull: "Not applicable to SELL" → APPROVE
   │   ├─ Bear: "Elon musk risk, regulatory headwinds" → APPROVE
   │   ├─ Risk: "Reduce exposure to EVs, but position small" → VETO
   │   └─ Committee: Risk vetoes (exposure already 2% TSLA) → VETO
   │
   └─ Agent verdicts stored in DB

7. RISK CONTROLLER (9:44 AM)
   ├─ AAPL BUY approved by agents:
   │   ├─ Current positions: 8
   │   ├─ Max positions: 15 ✓
   │   ├─ Current tech exposure: 35%
   │   ├─ Max single stock: 10% ✓
   │   ├─ Risk budget: 0.5% of $100k account = $500
   │   ├─ Target entry: $185.50
   │   ├─ Stop loss: $182.00
   │   ├─ Risk per share: $3.50
   │   ├─ Quantity: $500 / $3.50 = 143 shares (conservative 128 to account for slippage)
   │   ├─ Portfolio exposure if filled: 87% ✓
   │   └─ VERDICT: APPROVED, sized order: BUY 128 AAPL at market
   │
   ├─ TSLA SELL already vetoed by agents → no risk check needed
   │
   └─ Risk verdict stored in DB

8. EXECUTION (9:45 AM)
   ├─ Submit order to Alpaca:
   │   ├─ BUY 128 AAPL market order
   │   ├─ Stop loss alert: $182.00
   │   ├─ Target alert: $189.00
   │   └─ Order ID: ALPaca_12345
   │
   ├─ Order accepted, placed
   ├─ Wait for fill (usually instant for large cap)
   ├─ Fill received: 128 @ $185.52 = $23,746.56
   ├─ Position recorded in DB:
   │   ├─ Ticker: AAPL
   │   ├─ Quantity: 128
   │   ├─ Entry price: $185.52
   │   ├─ Stop: $182.00
   │   ├─ Target: $189.00
   │   └─ Trade ID: trade_20240116_001
   │
   └─ Update portfolio state in DB

9. AUDIT LOGGING
   ├─ Every step logged to PostgreSQL:
   │   ├─ event_001: "news_ingested" + sentiment scores
   │   ├─ event_002: "candidates_selected" + pool of 10
   │   ├─ event_003: "features_generated" + feature vectors
   │   ├─ event_004: "signal_generated" + AAPL BUY confidence 0.87
   │   ├─ event_005: "agent_critiques" + JSON from all 5 agents
   │   ├─ event_006: "risk_approved" + sizing logic
   │   ├─ event_007: "order_submitted" + order ID
   │   ├─ event_008: "fill_confirmed" + price, qty, PnL
   │   └─ All linked to trade_20240116_001
   │
   └─ Trail complete, queryable, auditable

10. INTRADAY MONITORING (9:45 AM – 3:45 PM, every 30 min)
    ├─ 10:15 AM: AAPL at $186.20 → target $189, stop $182 → HOLD
    ├─ 10:45 AM: AAPL at $185.80 → no triggers
    ├─ 11:15 AM: AAPL at $184.50 → approaching stop, monitor
    ├─ 11:45 AM: AAPL at $183.20 → above stop but close, watch
    ├─ 12:15 PM: Portfolio drawdown +0.8% → no action (under 2% soft)
    ├─ [... continue monitoring ...]
    ├─ If AAPL hits $182.00: STOP-LOSS triggered
    │   ├─ SELL 128 AAPL at market
    │   ├─ Order filled at ~$181.95
    │   ├─ Loss: $574 (-0.57% of account)
    │   ├─ Trade closed, PnL recorded
    │   └─ Event logged: "stop_loss_triggered"
    │
    └─ If portfolio drawdown hits 3%: DE-RISK
        ├─ SELL 50% of all positions
        ├─ Reduce to 75% max exposure
        ├─ No new trades until recovery
        └─ Event logged: "emergency_de_risk_triggered"

11. END OF DAY (3:45 PM – 4:00 PM)
    ├─ Final portfolio snapshot:
    │   ├─ Total value: $99,426 (down $574 from AAPL stop)
    │   ├─ Unrealized PnL: +$1,200 (on remaining positions)
    │   ├─ Daily return: -0.57%
    │   ├─ Max drawdown: 0.8%
    │   └─ Positions: 8 (AAPL exited)
    │
    ├─ Afternoon run scheduled for 3:45 PM
    │   └─ Repeat steps 1-10 for pre-close decisions
    │
    └─ All logs, trades, audit trail stored & queryable
```

---

## Database Schema Overview

```
PostgreSQL + pgvector
─────────────────────

OHLCV (time-series market data)
├─ id (PK)
├─ ticker (FK to universe)
├─ date
├─ open, high, low, close, volume
└─ indexes: (ticker, date), (date)

Features (engineered features)
├─ id (PK)
├─ ticker (FK)
├─ date
├─ feature_1, feature_2, ... (technical indicators)
├─ sentiment_score
└─ indexes: (ticker, date)

News (raw news + embeddings)
├─ id (PK)
├─ title, content, source
├─ published_at
├─ embedding (pgvector, 768 dim)
├─ sentiment (manual or LLM)
└─ indexes: embedding (HNSW), published_at, sentiment

Signals (ML output)
├─ id (PK)
├─ timestamp
├─ ticker
├─ signal (BUY/SELL/HOLD)
├─ confidence
├─ expected_return_pct
├─ edge_score
└─ FK: training_run_id

Agent_Critiques (LLM agent responses)
├─ id (PK)
├─ timestamp
├─ signal_id (FK)
├─ agent (analyst/bull/bear/risk/committee)
├─ response_json
├─ recommendation (APPROVE/VETO/REDUCE)
└─ rationale

Risk_Decisions (risk controller verdicts)
├─ id (PK)
├─ timestamp
├─ signal_id (FK)
├─ agent_recommendation (FK)
├─ risk_verdict (APPROVED/REJECTED)
├─ sizing_logic (JSON)
├─ quantity
├─ stop_loss, target
└─ rationale

Orders (submitted to broker)
├─ id (PK)
├─ timestamp
├─ risk_decision_id (FK)
├─ broker_order_id (Alpaca)
├─ ticker, action, quantity, order_type
├─ status (submitted/filled/cancelled)
└─ created_at, filled_at

Trades (completed fills)
├─ id (PK)
├─ order_id (FK)
├─ ticker, action, quantity
├─ fill_price, fill_time
├─ commissions, slippage
├─ trade_cost
└─ stop_loss, target, trade_id

Positions (open positions)
├─ id (PK)
├─ ticker
├─ quantity, entry_price, entry_date
├─ current_price, unrealized_pnl, unrealized_pnl_pct
├─ stop_loss, target
└─ last_update

Portfolio_State (snapshots)
├─ id (PK)
├─ timestamp
├─ total_value, cash, positions_value
├─ unrealized_pnl, unrealized_pnl_pct
├─ daily_drawdown, max_daily_drawdown
├─ num_positions, max_exposure
└─ snapshot_json

Audit_Log (immutable decision trail)
├─ id (PK)
├─ timestamp
├─ event_type (signal_generated, agent_critique, ...)
├─ component (ml, agents, risk, execution)
├─ ticker (if applicable)
├─ event_data_json
└─ trace_id (links all events for 1 trade)

Model_Versions (ML model tracking)
├─ id (PK)
├─ model_type (xgboost)
├─ version, training_date
├─ training_data_date_range
├─ hyperparameters, backtest_metrics
├─ artifact_path
└─ is_active
```

---

## Data Flow Diagram: News → Trade

```
RSS Feeds (SEC, Yahoo, Reuters, etc)
   │
   ├─→ Parse headlines
   │   └─→ Sentiment (Ollama): +1 (positive), 0 (neutral), -1 (negative)
   │
   ├─→ Embed headline + content
   │   └─→ LLM embedding: 768-dim vector
   │
   ├─→ Store in pgvector (news table)
   │   └─→ Indexed with HNSW for fast similarity search
   │
   ├─→ Query by RAG: "Find news similar to AAPL recent moves"
   │   └─→ Return top-K most similar, rank by recency + sentiment
   │
   ├─→ Feature engineering: news_sentiment_score
   │   └─→ Aggregate sentiment of top-K related news
   │
   ├─→ ML inference: BUY/SELL/HOLD + confidence
   │   └─→ Signal depends on sentiment + technical indicators
   │
   ├─→ Agent critique: "Does sentiment match news context?"
   │   └─→ RAG query: retrieve original news for agent context
   │
   ├─→ Risk controller: Size trade based on signal + confidence
   │   └─→ 0.5% risk per trade, adjusted for confidence
   │
   ├─→ Execution: Submit order to Alpaca
   │   └─→ Track fill price, record trade
   │
   └─→ Audit logging: Link every step to original news
       └─→ Query trail: "Why did we BUY AAPL on Jan 16?"
           Answer: "Earnings beat (from news) → sentiment +0.9 → 
                    XGBoost BUY 0.87 confidence → Agents approved → 
                    Risk sized 128 shares → Filled @ 185.52"
```

---

## Twice-Daily Run Schedule (EST)

```
Morning Run: 9:35 AM ET
├─ Market opens at 9:30 AM
├─ Run starts at 9:35 AM (5 min for premarket digestion)
├─ News from overnight + premarket
├─ Ingest, analyze, execute
├─ Complete by 9:50 AM
└─ Intraday monitoring: 9:50 AM – 3:45 PM

Afternoon Run: 3:45 PM ET
├─ Run starts 15 min before close (3:45 PM)
├─ News from morning + afternoon
├─ Analyze, execute entries/exits
├─ Closes before market close (4:00 PM)
└─ Intraday monitoring: until 4:00 PM close

Intraday Monitoring: 9:50 AM – 4:00 PM (every 15–30 min, no agents)
├─ Fetch latest prices
├─ Check stops (execute if triggered)
├─ Check drawdown (de-risk if >2% soft limit)
├─ No new decision runs (only emergencies)
└─ Log all activity to audit trail
```

---

## Risk Control Hierarchy

```
Level 1: ML Proposes (Only Source of New Trades)
├─ BUY, SELL, HOLD signals
├─ Confidence + expected return
└─ No overrides possible from agents

Level 2: Agents Critique (Soft Gate)
├─ Can APPROVE, VETO, or REDUCE
├─ Cannot invent trades
├─ Cannot increase exposure
└─ Rationale: "Why veto?" logged

Level 3: Risk Controller (Hard Gate)
├─ Enforces position sizing (0.5% risk/trade)
├─ Enforces portfolio constraints:
│  ├─ Max 15 positions
│  ├─ Max 10% single stock
│  ├─ Max 100% exposure
│  └─ Max 2% soft / 3% hard drawdown
├─ Cannot be overridden
└─ Pure code, no exceptions

Level 4: Intraday Enforcement (No Agents)
├─ Real-time stop-loss execution
├─ Drawdown-triggered de-risking
├─ Emergency rules (gap/volatility)
├─ Deterministic, no discretion
└─ Immediate execution

Trust Hierarchy:
────────────────
Risk Controller (Absolute) > Agents (Soft) > ML (Proposed)
```

---

## Error Handling Strategy

```
ML Inference Fails
├─ Log error: "ml_inference_failed"
├─ Skip that ticker
├─ Continue with others
└─ Alert: "5 tickers failed, processed 45"

Agent Critique JSON Invalid
├─ Log error: "agent_json_parse_failed"
├─ Retry agent (1 attempt)
├─ If still invalid: default to VETO (conservative)
├─ Log fallback: "defaulted_to_veto"
└─ Continue with other tickers

Alpaca API Timeout
├─ Retry (3 attempts)
├─ If failed: log error, pause orders
├─ Alert: "Alpaca API unavailable for 5 min"
├─ Try next scheduled run
└─ No position taken if API unavailable

Missing Data (OHLCV, News)
├─ Use most recent available
├─ Log lag: "data_stale_by_X_minutes"
├─ If > 30 min stale: skip ticker
└─ Continue with available data

Drawdown Breach (3% hard limit)
├─ IMMEDIATE: Stop all new trades
├─ IMMEDIATE: Reduce all positions by 50%
├─ Log emergency: "drawdown_hard_limit_triggered"
├─ Alert: "PORTFOLIO EMERGENCY DE-RISK ACTIVATED"
├─ Disable new trades until recovery
└─ Require manual review before re-enabling

All errors logged to PostgreSQL + console
├─ Event_id + timestamp + component + reason
├─ Trace_id to link to any affected trades
└─ Queryable for root-cause analysis
```

---

## Performance Considerations

```
Latency Budget (per decision run, ~30 min total)
─────────────────────────────────────────────────
News Ingestion:     5 min  (fetch, parse, embed)
Candidate Select:   2 min  (query news, apply rules)
Data Fetch:         3 min  (Alpaca + Yahoo OHLCV)
Feature Engineer:   5 min  (10 tickers × 30 sec each)
ML Inference:       2 min  (XGBoost is fast)
Agent Critique:     5 min  (1 min per BUY/SELL proposal, ~5 proposals)
Risk Controller:    2 min  (sizing, constraints check)
Execution:          3 min  (submit orders, wait for fills)
Audit Logging:      1 min  (batch insert to PostgreSQL)
─────────────────
Total:             ~28 min

Intraday Check Overhead (every 30 min)
─────────────────────────────────────
Fetch prices:       10 sec
Check stops:        10 sec
Check drawdown:      5 sec
Determine action:    5 sec
Execute (if needed): 10 sec
─────────────────
Total:             ~40 sec per check (5-6 checks/day)

Database Indexes (Critical)
───────────────────────────
OHLCV:               (ticker, date) → daily fetch
Features:            (ticker, date) → feature engineering
News:                embedding (HNSW) → RAG queries
News:                published_at → recent news filter
Positions:           ticker → position updates
Audit_Log:          trace_id, timestamp → audit trail
```

---

## Monitoring & Observability

```
Key Metrics Logged Every Run
─────────────────────────────
• Candidates analyzed: count
• Signals generated: BUY/SELL/HOLD distribution
• Agent agreement rate: % of unanimous approvals
• Risk rejections: % of proposals rejected
• Execution rate: % of approved orders filled
• Latency per component: milliseconds
• Error rate: % of failures per component
• Portfolio stats: total value, exposure %, drawdown %

Queries You'll Run
──────────────────
1. "Show me the audit trail for AAPL BUY on Jan 16"
2. "What % of agent critiques led to vetoes?"
3. "Which news sources drive the most profitable signals?"
4. "What's my Sharpe ratio over last 4 weeks?"
5. "How often did stops trigger vs. targets?"
6. "What's the average agent response latency?"

Alerts to Monitor
─────────────────
• Error rate > 5% per run → investigate
• Agent latency > 10 sec per critique → optimize prompts
• Alpaca API failures → fallback to backup
• Drawdown soft limit (2%) → monitor position concentration
• Same ticker rejected by risk > 3x → review sizing logic
```

---

## Testability Strategy

```
Unit Tests (Isolated)
────────────────────
• Sentiment score logic: +1/-1/0 based on keywords
• Feature engineering: RSI, MACD, momentum
• Position sizing: 0.5% risk → quantity
• Constraint checks: max exposure, single stock, max positions
• JSON parsing: agents' structured responses

Integration Tests (Component Pairs)
───────────────────────────────────
• Candidate selector → ML: signals generated for candidates
• ML → Risk: risk controller correctly sizes proposals
• Risk → Execution: orders submitted with correct stops/targets
• Agents → Committee: veto logic synthesized correctly
• Execution → Audit: all trades logged with full trail

End-to-End Tests (Full Pipeline)
────────────────────────────────
1. Bullish signal: news → candidate → ML BUY → agents APPROVE → risk OK → order filled
2. Bearish signal: news → candidate → ML SELL → agents veto → no order
3. Risk breach: 5 orders enter, drawdown hits 3% → emergency de-risk → positions reduced
4. Stop triggered: position enters, price hits stop → order filled, trade closed
5. Multi-candidate day: 10 candidates, 5 signals, 3 approved, 2 filled, all audited

Backtest Tests (Historical)
──────────────────────────
1. 2+ years historical data
2. Run full pipeline on each day
3. Measure: Sharpe, max drawdown, win rate, edge
4. Sensitivity: adjust hyperparams, retest
5. Validate: backtest >0.5 Sharpe before live

Mock/Fixture Data
─────────────────
• Mock news: sample RSS feeds with known sentiments
• Mock OHLCV: historical data or synthetic
• Mock agents: JSON responses with known recommendations
• Mock Alpaca: sandbox paper trading account
```

---

This document is your visual reference while building. Refer back to it during each phase!

