# Project Summary & Quick Reference

**Project:** Institutional-Style Automated Trading System  
**Status:** Design complete, ready for implementation (Phase 1)  
**Timeline:** 6–8 weeks to v1 completion  
**Updated:** January 16, 2026

---

## What You're Building

A fully automated daily trading system that:

1. **Listens to news** – identifies trading opportunities
2. **Analyzes with ML** – generates BUY/SELL/HOLD signals (XGBoost)
3. **Critiques with agents** – local LLM validates decisions
4. **Controls with rules** – hard constraints on risk & position sizing
5. **Executes & audits** – every trade is tracked, logged, and explainable

**Core philosophy:** News routes attention. ML proposes trades. Agents validate. Rules enforce discipline.

---

## System Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR (Twice Daily)                │
│                                                              │
│  Morning Run (9:35 ET) | Afternoon Run (3:45 ET)            │
└──────────────────────────────────────────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │                   NEWS INGESTION                 │
    │   (RSS → Parse → Embed → Store in pgvector)      │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │              CANDIDATE SELECTION                 │
    │  • News-driven (earnings, M&A, guidance)         │
    │  • Market-driven (gaps, volume, volatility)      │
    │  • Portfolio-driven (open positions, exits)      │
    │  • Baseline (rotating blue-chip coverage)        │
    │  → Output: List of tickers to analyze            │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │          FEATURE ENGINEERING & FETCH             │
    │  • OHLCV (Alpaca + Yahoo)                        │
    │  • Technical indicators (RSI, MACD, etc)         │
    │  • News sentiment (LLM extraction)               │
    │  → Output: Feature vectors for each ticker       │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │            ML SIGNAL ENGINE (XGBoost)            │
    │  • Load trained model                            │
    │  • Generate BUY/SELL/HOLD signals                │
    │  • Confidence + expected return + edge score     │
    │  → Output: Proposals (only BUY/SELL)             │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │          AGENT CRITIQUE SYSTEM (Ollama)          │
    │  • Market Analyst (regime assessment)            │
    │  • Bull (best-case thesis)                       │
    │  • Bear (counter-thesis)                         │
    │  • Risk Manager (event/exposure risk)            │
    │  • Committee (synthesis & recommendation)        │
    │  → Output: APPROVE | VETO | REDUCE               │
    │  (Agents never invent trades, only critique ML)  │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │          RISK CONTROLLER (Hard Rules)            │
    │  • Position sizing (0.5% per trade)              │
    │  • Portfolio constraints (10-15 positions)       │
    │  • Max exposure (100%), single stock (10%)       │
    │  • Stop/target calculation                       │
    │  • Drawdown limits (2% soft, 3% hard)            │
    │  → Output: Sized orders ready for execution      │
    │  (Pure code, zero overrides)                     │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │      EXECUTION ENGINE (Alpaca Paper API)         │
    │  • Submit market orders                          │
    │  • Track fills + PnL                             │
    │  • Audit log every trade                         │
    │  → Output: Filled trades recorded in DB          │
    └───────────────────────┬──────────────────────────┘
                            ↓
    ┌──────────────────────────────────────────────────┐
    │          INTRADAY MONITORING (No Agents)         │
    │  • Every 15-30 min checks                        │
    │  • Stop-loss enforcement                         │
    │  • Drawdown monitoring                           │
    │  • Emergency rules (gaps, volatility)            │
    │  → Deterministic safety only                     │
    └──────────────────────────────────────────────────┘
```

---

## Key Design Decisions (Locked ✅)

| Aspect | Decision | Why |
|--------|----------|-----|
| **Data Sources** | RSS + Alpaca + Yahoo | Free, reliable, news-first focus |
| **ML Model** | XGBoost (weekly retraining) | Fast, interpretable, proven |
| **LLM Runtime** | Ollama + Mistral 7B | Local, deterministic, no API calls |
| **Universe** | S&P 100–150 stocks | Blue-chip liquidity, reasonable scope |
| **Max Portfolio** | 10–15 positions | Risk control, attribution |
| **Risk per Trade** | 0.5% of account | Conservative, professional standard |
| **Max Drawdown** | 2% soft / 3% hard | Prevent death spirals |
| **Trading Mode** | Paper-only (v1) | Validation before live |
| **Order Type** | Market orders | Simple, liquid blue chips |
| **Monitoring** | Twice daily + 15-30 min intraday | Daily cadence sufficient |
| **Agent Authority** | Reduce/veto only, never create | ML is alpha source, LLM validates risk |
| **Audit Trail** | Full + queryable | Decision traceability |

See [DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md) for full details.

---

## Technology Stack (Locked)

| Layer | Technology |
|-------|------------|
| **Language** | Python 3.10+ |
| **Database** | PostgreSQL + pgvector |
| **ML** | XGBoost |
| **LLM** | Ollama + Mistral 7B |
| **Broker API** | Alpaca (paper trading) |
| **Deployment** | Docker + Docker Compose |
| **Monitoring** | Structured JSON logs |

---

## Implementation Phases (8 weeks)

| Phase | Duration | Goal | Success Criteria |
|-------|----------|------|------------------|
| **1: Infrastructure** | Week 1–2 | Docker, DB, Ollama ready | `docker-compose up` works |
| **2: Data Layer** | Week 2–3 | News + OHLCV flowing | 30-day data + features for S&P 100 |
| **3: ML Pipeline** | Week 3–4 | XGBoost training & inference | Backtest Sharpe > 0.5 |
| **4: Agent System** | Week 4–5 | LLM critiques working | <5 sec per critique, JSON parsing 100% |
| **5: Risk & Execution** | Week 5–6 | Orders submitted & filled | 10 test orders tracked |
| **6: Orchestration** | Week 6–7 | Twice-daily runs complete | Full pipeline executes, audit trail present |
| **7: Testing** | Week 7–8 | Full test suite passing | Unit + integration + E2E tests green |
| **8: Paper Trading** | Week 8+ | Live validation for 4 weeks | 4 weeks stable, ready for live |

See [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) for detailed breakdown.

---

## Directory Structure

```
market_prediction/
├── config/              # Global settings, models, agents, universe
├── src/
│   ├── news/            # News ingestion & RAG
│   ├── candidates/      # Candidate selection logic
│   ├── features/        # Feature engineering pipeline
│   ├── ml/              # XGBoost training & inference
│   ├── agents/          # Ollama agent system
│   ├── risk/            # Risk controller & constraints
│   ├── execution/       # Alpaca API integration
│   ├── scheduler/       # Orchestration & monitoring
│   ├── db/              # PostgreSQL interface
│   └── utils/           # Logging, metrics, helpers
├── tests/               # Unit, integration, E2E tests
├── docker/              # Dockerfiles, compose
├── data/                # Model artifacts, backtest results
├── docs/                # Architecture, API, deployment
└── scripts/             # CLI tools (training, backtesting, etc)
```

---

## Component Contracts

**Every component communicates via documented JSON interfaces.** See [API_CONTRACTS.md](./API_CONTRACTS.md) for:
- Candidate selector input/output
- ML signal format
- Agent critique structure
- Risk controller output
- Execution payload
- Audit log schema

---

## Critical Decisions Made

### ✅ ML Authority
- ML is the **only** source of new trade proposals
- Agents critique risk and thesis, never invent trades
- Prevents LLM hallucinations from becoming trades

### ✅ Agent Limits
- Agents can reduce or veto trades
- Agents **cannot** increase exposure or create trades
- Keeps institutional risk discipline

### ✅ Risk as Hard Code
- Risk controller is pure Python, no overrides
- Enforces sizing, constraints, drawdown limits
- Cannot be bypassed by agents or operators

### ✅ Paper-First Approach
- v1 is paper trading only (Alpaca sandbox)
- Live trading only after 4+ weeks of validation
- Confidence + reproducibility before risking real capital

### ✅ News-Driven Focus
- Candidate selection starts with news (not arbitrary scanning)
- Reduces false signals, focuses compute on relevant candidates
- Market data + portfolio state supplement news for routing

### ✅ Full Audit Trail
- Every decision logged: signal → agent → risk → execution
- Enables attribution analysis and regulatory compliance
- Queryable PostgreSQL + structured JSON logs

---

## What's NOT Included (Deferred to v1.1+)

- LSTM / ensemble models
- Finnhub structured events
- Limit order optimization
- Sector/industry constraints
- S&P 500 expansion
- Slack/email alerts
- Options / derivatives
- Live trading (v1 is paper only)

---

## Next Step: Phase 1

**Start Date:** [When you're ready]

**Deliverables:**
1. Docker Compose with postgres, ollama, app services
2. PostgreSQL schema + pgvector extension
3. Ollama Mistral 7B loaded & tested
4. Config files (settings, models, agents, risk rules)
5. All services communicate & are persistent

**Definition of Done:** `docker-compose up` and all services run without errors.

---

## How to Navigate the Docs

1. **[DESIGN_DECISIONS.md](./DESIGN_DECISIONS.md)** – All locked decisions & rationale (reference)
2. **[API_CONTRACTS.md](./API_CONTRACTS.md)** – Component communication formats (implementation guide)
3. **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** – Phase-by-phase breakdown (execution plan)
4. **[This document](./README.md)** – Overview & quick reference

---

## Questions?

Use this checklist to verify design is locked:

- [ ] Data sources decided (RSS + Alpaca + Yahoo)
- [ ] ML model locked (XGBoost, weekly retrain)
- [ ] Agents defined (5 roles, reduce/veto only)
- [ ] Universe sized (S&P 100–150)
- [ ] Risk constraints set (0.5% per trade, 2%/3% drawdown)
- [ ] Trading mode confirmed (paper-only v1)
- [ ] Execution locked (market orders, Alpaca)
- [ ] Tech stack confirmed (Python, PostgreSQL, Docker)

**If all checkboxes are ✅, you're ready to build Phase 1.**

---

**Good luck! Start with Phase 1 whenever you're ready.** 🚀

