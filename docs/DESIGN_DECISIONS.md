# Design Decisions – Market Prediction Trading System

**Last Updated:** January 16, 2026  
**Status:** Locked for v1 Implementation

---

## Executive Summary

This document locks all major architectural and operational decisions for v1. Decisions are either:
- ✅ **Locked** – Implement as specified
- ⏭️ **Deferred** – Plan for v1.1+, but don't implement now

---

## 1. Data Sources

### News & Events
| Decision | Details |
|----------|---------|
| ✅ **Primary** | RSS feeds (SEC, financial news sites) |
| ⏭️ **Later** | Finnhub (structured event tags) |
| **Implementation** | Custom RSS parser + LLM sentiment extraction |
| **Rationale** | RSS is free, reliable, and sufficient for v1. Structured events add overhead. |

### Market Data
| Decision | Details |
|----------|---------|
| ✅ **Primary** | Alpaca API (paper trading) |
| ✅ **Secondary** | Yahoo Finance (backup OHLCV) |
| ⏭️ **Later** | Fear and Greed index |
| **Training Data** | Yahoo Finance (historical) |
| **Rationale** | Alpaca is integrated for execution. Yahoo is cheap and reliable for history. |

### Sentiment Analysis
| Decision | Details |
|----------|---------|
| ✅ **Method** | Built-in via LLM (Ollama) + RAG |
| **Approach** | Prompt Mistral 7B to score news as positive/negative/neutral, compare to historical themes |
| **No external** | Don't use sentiment APIs (higher cost, less control) |
| **Rationale** | Keeps system fully local, no external dependencies beyond data fetch. |

---

## 2. Machine Learning

### Model Selection
| Decision | Details |
|----------|---------|
| ✅ **Primary (v1)** | XGBoost |
| **Input** | Daily OHLCV + technical features + news sentiment |
| **Output** | BUY / SELL / HOLD + confidence (0-1) + expected return (%) |
| **Prediction Horizon** | 1-day forward return / direction |
| ⏭️ **Later** | LSTM ensemble (only after v1 is stable & profitable) |
| **Rationale** | XGBoost is fast, interpretable, and industry-standard. LSTM adds complexity with marginal gains for daily trading. |

### Training Cadence
| Decision | Details |
|----------|---------|
| ✅ **Frequency** | Weekly retraining |
| ✅ **Inference** | Daily (twice per trading day) |
| **Retraining Window** | 2+ years rolling history |
| **Rationale** | Weekly captures market regime changes without overfitting. Daily inference keeps signals fresh. |

### Model Governance
| Decision | Details |
|----------|---------|
| ✅ **Authority** | ML is the **only** component allowed to propose new trades |
| ✅ **Signals** | BUY/SELL/HOLD only |
| ✅ **No agents** | LLM agents cannot invent or override ML trades |
| **Rationale** | ML is your alpha source. Agents critique risk, not fundamentals. Prevents hallucination-driven mistakes. |

---

## 3. Agent System

### LLM Model
| Decision | Details |
|----------|---------|
| ✅ **Primary** | Mistral 7B (Ollama) |
| ✅ **Backup** | Llama 3.x 8B (optional comparison) |
| **Runtime** | Ollama (local, no external API calls) |
| **Rationale** | Mistral is fast, accurate for structured tasks. Ollama keeps everything local and deterministic. |

### Agent Roles & Authority
| Decision | Details |
|----------|---------|
| ✅ **Market Analyst** | Assess regime, identify anomalies |
| ✅ **Bull** | Best-case thesis given the signal |
| ✅ **Bear** | Counter-thesis, risks |
| ✅ **Risk Manager** | Event/exposure risk assessment |
| ✅ **Committee** | Synthesize critiques, recommend veto or approval |
| **Authority** | **Reduce or veto only** – never create, never increase exposure |
| **Rationale** | Keeps LLM in a gatekeeping role, prevents hallucination. |

### Response Format
| Decision | Details |
|----------|---------|
| ✅ **Format** | Strict structured JSON only |
| **Parsing** | No free-text parsing. Prompt agents for JSON output. |
| **Validation** | Reject non-JSON responses, retry or skip. |
| **Rationale** | Removes ambiguity, makes audit trails precise. |

---

## 4. Universe & Portfolio Constraints

### Universe Size
| Decision | Details |
|----------|---------|
| ✅ **Scope** | S&P 100–150 stocks |
| **Coverage** | Blue-chip, highly liquid, reliable news coverage |
| **Why not 500?** | Compute cost, correlation complexity, no news delta for micro-cap stocks |
| ⏭️ **Later** | Expand to S&P 500 after v1 is stable |

### Position Limits
| Decision | Details |
|----------|---------|
| ✅ **Max concurrent** | 10–15 positions |
| **Rationale** | Easier risk control, lower correlation risk, better attribution analysis |
| **Min position** | No minimum (size rules handle allocation) |

### Risk per Trade
| Decision | Details |
|----------|---------|
| ✅ **Risk Budget** | 0.5% of account per trade |
| **Rationale** | Conservative, survivable through drawdowns, professional standard |
| **Sizing** | Risk-per-trade sizing uses Kelly-like formula (detailed in risk/sizing.py) |

### Portfolio Exposure
| Decision | Details |
|----------|---------|
| ✅ **Max long exposure** | 100% (fully invested when candidates align) |
| ✅ **Max short exposure** | 0% (long-only v1) |
| ✅ **Max single position** | 10% of portfolio |
| ✅ **Sector limits** | None (v1) – let diversification emerge from universe |

### Drawdown Enforcement
| Decision | Details |
|----------|---------|
| ✅ **Soft Limit** | 2% intraday drawdown (alert, log, monitor) |
| ✅ **Hard Limit** | 3% drawdown (de-risk: reduce all positions by 50%, stop new trades) |
| **Recovery** | Re-enable after 1 full trading day of recovery |
| **Rationale** | Prevents death spirals, preserves capital, forces discipline |

---

## 5. Execution

### Trading Mode
| Decision | Details |
|----------|---------|
| ✅ **v1 Mode** | Paper trading only (Alpaca paper account) |
| **Architecture** | Live-ready (trivial switch: env var + API key) |
| **Why Paper First** | Stability, attribution validation, confidence building |
| ⏭️ **Live Trading** | Only after 4+ weeks of validated paper trading |

### Order Types
| Decision | Details |
|----------|---------|
| ✅ **Entry** | Market orders |
| ✅ **Exit** | Market orders |
| ⏭️ **Later** | Limit orders (for cost optimization) |
| **Slippage Model** | None (paper) / track real slippage live |
| **Rationale** | Market orders are simple, reliable. Blue-chip liquidity makes slippage minimal. |

### Monitoring Frequency
| Decision | Details |
|----------|---------|
| ✅ **Scheduled Runs** | Twice daily (morning ~9:35am, pre-close ~3:45pm ET) |
| ✅ **Intraday Monitoring** | Event-driven + periodic (15–30 min checks) |
| **Full Decision Runs** | Only at scheduled times (morning/pre-close) |
| **Intraday Actions** | Stops, drawdown rules, emergency rules only (no agents) |
| **Rationale** | Daily cadence is sufficient. Real-time monitoring adds operational overhead with marginal benefit. |

---

## 6. Logging & Observability

### Audit Trail Depth
| Decision | Details |
|----------|---------|
| ✅ **Full Audit** | Log every decision & its reasoning |
| **Components Logged** | Features snapshot, ML outputs, news citations (RAG), agent JSON, final decisions, rule overrides, execution + PnL |
| **Traceability** | Every trade is traceable to: signal → agents → risk check → execution |
| **Rationale** | Becomes your biggest asset for improvement. Enables real attribution analysis. |

### Log Format
| Decision | Details |
|----------|---------|
| ✅ **Format** | Structured JSON (each event is a JSON object) |
| **Storage** | Local files + PostgreSQL (duplicate for querying) |
| **Example** | `{"timestamp": "...", "event": "signal_generated", "ticker": "AAPL", "signal": "BUY", "confidence": 0.87, ...}` |

### Alerts
| Decision | Details |
|----------|---------|
| ✅ **v1 Method** | Log files + console output |
| ⏭️ **Later** | Slack/email integration |
| **Rationale** | Don't overbuild alerting early. Log files are sufficient. Add Slack later if needed. |

---

## 7. Component Authority & Control Flow

### Decision Hierarchy (Most → Least Powerful)
1. **Risk Controller** (Hard Rules)
   - Last authority. Cannot be overridden.
   - Can veto any trade, reduce positions, halt trading.

2. **Agent Committee** (Soft Rules)
   - Can reduce or veto trades proposed by ML.
   - Cannot invent trades or increase exposure.

3. **ML Signal Engine** (Alpha Source)
   - Only component that proposes new trades.
   - Generates BUY/SELL/HOLD + confidence.

4. **Candidate Selector** (Attention Router)
   - Decides what gets analyzed (not what gets traded).
   - News, market data, portfolio state guide analysis.

5. **Intraday Enforcement** (Safety Only)
   - No agents. Pure deterministic rules.
   - Stops, drawdown, emergency rules.

---

## 8. System Integration Points

### Data Flow (Twice Daily)
```
News Ingestion
    ↓
Candidate Selection (news-driven, market-driven, portfolio-driven, baseline)
    ↓
Feature Engineering (OHLCV + technical + sentiment)
    ↓
ML Inference (XGBoost → BUY/SELL/HOLD + confidence)
    ↓
Agent Critique (Analyst → Bull → Bear → Risk → Committee)
    ↓
Risk Controller (sizing, constraints, stops, emergency rules)
    ↓
Execution (Alpaca market orders)
    ↓
Audit Logging (full trail)
```

### Intraday (No Agents)
```
Market Data + Portfolio State
    ↓
Stop-Loss Enforcement
    ↓
Drawdown Monitoring
    ↓
Emergency Rules (gaps, volatility)
    ↓
Audit Logging
```

---

## 9. Technology Stack (Locked)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Language** | Python 3.10+ | Ecosystem (pandas, scikit-learn, Alpaca SDK) |
| **Database** | PostgreSQL + pgvector | ACID compliance, vector search for RAG, proven reliability |
| **ML** | XGBoost | Fast, interpretable, industry-standard |
| **LLM** | Ollama + Mistral 7B | Local, deterministic, no API calls |
| **Execution** | Alpaca API | Paper + live trading, no commissions paper |
| **Deployment** | Docker + Docker Compose | Reproducibility, easy migration to home server |
| **Monitoring** | Structured JSON logs | Queryable, audit-friendly |

---

## 10. Known Deferred Decisions (v1.1+)

| Feature | Reason for Deferral |
|---------|-------------------|
| LSTM / Ensemble models | Complexity; XGBoost sufficient for initial validation |
| Finnhub structured events | Cost & setup overhead; RSS sufficient |
| Limit orders | Slippage optimization (market orders fine for blue chips) |
| Sector/industry constraints | Not needed for 10-15 position portfolio |
| S&P 500 expansion | Compute & correlation complexity |
| Slack/email alerts | Logs sufficient for v1; add if needed |
| Live trading | After 4+ weeks of stable paper trading |
| Options / derivatives | Out of scope for equity system |
| PDT multi-account strategy | Requires $50K+ capital; evaluate after v1 validation |
| Crypto day trading | Add when crypto data integrated (v1.1+) |

---

## 11. Pattern Day Trader (PDT) Compliance

| Decision | Details |
|----------|---------|
| ✅ **v1 Strategy** | "Avoid" – no same-day round-trip trades |
| ✅ **Min hold** | At least 1 full business day before exit |
| ✅ **Crypto** | Not subject to PDT; allowed for future crypto signals |
| ⏭️ **Multi-account** | Track day trade counts per account (v1.1+) |
| ⏭️ **Hold-swing** | Formalize minimum hold windows (v1.1+) |
| **Rationale** | Most conservative approach prevents PDT flag entirely. Aligns with swing-trading philosophy. Allows later pivot to more active strategies if capital >$25K. See [PDT_RULES.md](PDT_RULES.md) for 4 strategies & implementation details. |

---

## 12. Success Metrics (v1)

- [ ] Full daily runs execute without errors (99%+ uptime)
- [ ] Audit logs are complete and traceable
- [ ] Backtests show positive Sharpe ratio (>0.5)
- [ ] Paper trading: 4 weeks, no drawdown breach, consistent execution
- [ ] Agent system provides meaningful critiques (logged for review)
- [ ] Risk controller successfully enforces all constraints
- [ ] Zero PDT violations (all positions held ≥1 business day before exit)

---

## Approval

- **Designed by:** Ryan
- **Locked:** January 16, 2026
- **PDT Rules Added:** January 20, 2026
- **Next review:** After 4-week paper trading validation

