# Quick Visual Reference

This page is your single-page visual summary. Bookmark it.

---

## System at a Glance

```
┌─────────────────────────────────────────────────────────┐
│           AUTOMATED TRADING SYSTEM (v1)                 │
│        News → ML → Agents → Risk → Execution           │
└─────────────────────────────────────────────────────────┘

INPUT                          PROCESS                      OUTPUT
═════════════════════════════════════════════════════════════════════

RSS Feeds              →  News Ingestion           →  Candidate List
Market Data           →  Candidate Selection      →  Tickers to Analyze
Open Positions        →  Feature Engineering      →  Feature Vectors
Portfolio State       →  ML Inference (XGBoost)   →  BUY/SELL/HOLD
                      →  Agent Critique (Ollama)  →  APPROVE/VETO
                      →  Risk Controller          →  Sized Order
                      →  Execution (Alpaca)       →  Filled Trade
                      →  Audit Logging            →  Queryable Trail

INTRADAY (No Agents)  →  Monitor Prices           →  Stop-Loss / De-Risk
                      →  Check Drawdown           →  Emergency Rules
```

---

## Phased Timeline

```
PHASE 0: DESIGN ✅
├─ Locked all decisions
├─ Created 6 docs
└─ Ready for implementation

PHASE 1: INFRASTRUCTURE (Week 1-2)
├─ Docker + Docker Compose
├─ PostgreSQL + pgvector
├─ Ollama + Mistral 7B
└─ ✓ Success: docker-compose up

PHASE 2: DATA (Week 2-3)
├─ News ingestion
├─ OHLCV fetching
├─ Feature engineering
└─ ✓ Success: Features for S&P 100

PHASE 3: ML (Week 3-4)
├─ XGBoost training
├─ Signal generation
├─ Backtesting framework
└─ ✓ Success: Backtest Sharpe >0.5

PHASE 4: AGENTS (Week 4-5)
├─ 5 agent roles
├─ Ollama integration
├─ JSON critique workflow
└─ ✓ Success: <5 sec per critique

PHASE 5: RISK & EXECUTION (Week 5-6)
├─ Position sizing
├─ Constraint enforcement
├─ Alpaca orders
└─ ✓ Success: 10 test orders filled

PHASE 6: ORCHESTRATION (Week 6-7)
├─ Twice-daily runs
├─ Intraday monitoring
├─ Audit logging
└─ ✓ Success: Full pipeline executes

PHASE 7: TESTING (Week 7-8)
├─ Unit tests
├─ Integration tests
├─ E2E scenarios
└─ ✓ Success: All tests passing

PHASE 8: PAPER TRADING (Week 8+)
├─ 4 weeks live validation
├─ Monitor for edge cases
├─ Performance analysis
└─ ✓ Success: Ready for live trading
```

---

## Locked Decisions (Quick Reference)

| Aspect | Decision | Why |
|--------|----------|-----|
| News | RSS feeds | Free, reliable |
| Market Data | Alpaca + Yahoo | Primary + backup |
| ML Model | XGBoost | Fast, interpretable |
| Retraining | Weekly | Captures regime changes |
| Universe | S&P 100-150 | Blue-chip liquidity |
| Max Positions | 10-15 | Risk control |
| Risk per Trade | 0.5% | Conservative, professional |
| Drawdown Hard Limit | 3% | Prevent death spirals |
| LLM | Ollama + Mistral 7B | Local, no API calls |
| Agent Authority | Reduce/veto only | ML is alpha source |
| Execution Mode | Paper (v1) | Validate before live |
| Order Type | Market orders | Liquid blue chips |
| Decision Runs | Twice daily | 9:35 AM, 3:45 PM ET |
| Intraday | Deterministic only | No agents, speed |
| Audit Trail | Full + queryable | Every decision logged |
| Deployment | Docker Compose | Reproducible |

---

## Data Flow (Simple)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. NEWS INGESTION (5 min)                                   │
│    Fetch RSS → Parse → Embed → Store in pgvector            │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CANDIDATE SELECTION (2 min)                              │
│    News-driven, Market-driven, Portfolio-driven, Baseline   │
│    → Output: [AAPL, MSFT, TSLA, ...] (10 tickers)           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. FEATURE ENGINEERING (5 min)                              │
│    OHLCV + Technical Indicators + Sentiment                 │
│    → Output: Feature vectors for ML                         │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. ML INFERENCE (2 min)                                     │
│    XGBoost → BUY/SELL/HOLD + Confidence + Expected Return   │
│    → Output: Proposals (BUY/SELL only)                      │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. AGENT CRITIQUE (5 min)                                   │
│    Analyst → Bull → Bear → Risk → Committee                 │
│    → Output: APPROVE / VETO / REDUCE                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. RISK CONTROLLER (2 min)                                  │
│    Sizing + Constraints + Stops/Targets                     │
│    → Output: Sized order or REJECT                          │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. EXECUTION (3 min)                                        │
│    Submit to Alpaca → Wait for fill → Record trade          │
│    → Output: Filled trade in DB                             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. AUDIT LOGGING (1 min)                                    │
│    Every step logged → PostgreSQL → Queryable               │
│    → Output: Complete decision trail                        │
└─────────────────────────────────────────────────────────────┘

TOTAL LATENCY: ~30 min per full decision run
RUNS: Twice daily (9:35 AM, 3:45 PM ET)
INTRADAY: 15-30 min checks (stops, drawdown, emergencies only)
```

---

## Component Responsibility Map

```
ML SIGNAL ENGINE
├─ Input: Features (OHLCV + technical + sentiment)
├─ Process: XGBoost inference
├─ Output: BUY / SELL / HOLD + confidence
├─ Authority: ONLY source of new trades
└─ Constraint: No overrides

LLM AGENT SYSTEM
├─ Input: ML proposal (BUY/SELL)
├─ Process: 5 agents critique (Analyst, Bull, Bear, Risk, Committee)
├─ Output: APPROVE / VETO / REDUCE
├─ Authority: Gate trades, reduce exposure
└─ Constraint: Cannot create trades, cannot increase exposure

RISK CONTROLLER
├─ Input: Agent recommendation + proposal
├─ Process: Sizing (0.5% risk) + Constraints (10-15 max, 3% DD)
├─ Output: Sized order or REJECT
├─ Authority: Final decision (hard rules)
└─ Constraint: Pure code, no exceptions

EXECUTION ENGINE
├─ Input: Risk-approved order
├─ Process: Submit to Alpaca, wait for fill
├─ Output: Filled trade + PnL
├─ Authority: Execute as directed
└─ Constraint: Market orders only, no discretion

INTRADAY MONITOR
├─ Input: Live market prices
├─ Process: Check stops, drawdown, emergencies
├─ Output: Stop-loss orders or de-risk actions
├─ Authority: Deterministic rules only
└─ Constraint: No agents, pure code
```

---

## Risk Hierarchy

```
LEVEL 1: ML PROPOSES (Authority)
├─ Only component allowed to propose trades
├─ Cannot be overridden
└─ Example: "BUY 100 AAPL at market"

                        ↓

LEVEL 2: AGENTS CRITIQUE (Soft Gate)
├─ Can reduce or veto proposals
├─ Cannot create trades
├─ Cannot increase exposure
└─ Example: "VETO due to tech sector concentration risk"

                        ↓

LEVEL 3: RISK CONTROLLER (Hard Gate)
├─ Enforces sizing rules (0.5% risk/trade)
├─ Enforces portfolio constraints:
│  ├─ Max 15 positions
│  ├─ Max 10% single stock
│  ├─ Max 100% exposure
│  └─ Max 2% soft / 3% hard drawdown
├─ Cannot be overridden
└─ Pure code, zero discretion

                        ↓

LEVEL 4: INTRADAY ENFORCEMENT (Real-Time)
├─ Stop-loss execution
├─ Drawdown-triggered de-risking
├─ Emergency rules (gaps, volatility)
├─ Deterministic, no agent involvement
└─ Immediate execution
```

---

## Document Navigation

```
START HERE
    ↓
DESIGN_PHASE_SUMMARY.md (this project folder)
    ↓
    ├─→ Want quick overview?
    │   → README.md (docs/)
    │
    ├─→ Want all decisions + rationale?
    │   → DESIGN_DECISIONS.md (docs/)
    │
    ├─→ Want component contracts?
    │   → API_CONTRACTS.md (docs/)
    │
    ├─→ Want system architecture?
    │   → ARCHITECTURE.md (docs/)
    │
    ├─→ Want build phases + timeline?
    │   → IMPLEMENTATION_ROADMAP.md (docs/)
    │
    └─→ Want phase-by-phase details?
        → Use TODO list (grouped by phase)
```

---

## Database Tables (Simplified)

```
OHLCV                  Features              News
├─ ticker              ├─ ticker              ├─ id
├─ date                ├─ date                ├─ title
├─ open/high/low/close ├─ rsi, macd, ...     ├─ embedding (pgvector)
├─ volume              ├─ sentiment_score     ├─ sentiment
└─ indexes             └─ indexes             └─ indexes

Signals                Agent_Critiques       Risk_Decisions
├─ ticker              ├─ signal_id           ├─ signal_id
├─ signal              ├─ agent               ├─ risk_verdict
├─ confidence          ├─ response_json       ├─ sizing
├─ expected_return     └─ recommendation      └─ quantity
└─ edge_score

Orders                 Trades                Positions
├─ ticker              ├─ ticker              ├─ ticker
├─ action              ├─ fill_price          ├─ quantity
├─ quantity            ├─ fill_time           ├─ entry_price
├─ status              ├─ commissions         ├─ current_price
└─ broker_order_id     └─ trade_cost          └─ unrealized_pnl

Portfolio_State        Audit_Log
├─ timestamp           ├─ timestamp
├─ total_value         ├─ event_type
├─ cash                ├─ component
├─ unrealized_pnl      ├─ ticker
└─ drawdown            ├─ event_data_json
                       └─ trace_id
```

---

## Trading Schedule

```
MONDAY – FRIDAY (US Market Trading Days)
═════════════════════════════════════════

Pre-Market (Before 9:30 AM ET)
├─ Overnight news ingestion
└─ Preparation for morning run

MORNING RUN: 9:35 AM ET (5 min after open)
├─ Ingest overnight news
├─ Select candidates
├─ Run ML + agents
├─ Execute approvals
└─ Complete by 9:50 AM

INTRADAY MONITORING: 9:50 AM – 3:45 PM ET
├─ Every 15–30 minutes
├─ Check stops + drawdown
├─ Execute emergencies (deterministic only)
└─ No new decision runs (agents offline)

AFTERNOON RUN: 3:45 PM ET (15 min before close)
├─ Ingest morning + afternoon news
├─ Select candidates
├─ Run ML + agents
├─ Execute entries/exits before close
└─ Complete by 3:55 PM

INTRADAY MONITORING: 3:55 PM – 4:00 PM ET (Market Close)
├─ Final stop checks
└─ Archive end-of-day state

POST-MARKET (After 4:00 PM ET)
├─ News continues (irrelevant for trading)
└─ Overnight waiting
```

---

## Success Indicators (Checkpoints)

| Phase | Checkpoint | Status |
|-------|-----------|--------|
| Phase 1 | `docker-compose up` starts all services | ⏳ Pending |
| Phase 2 | 30 days OHLCV + features for S&P 100 | ⏳ Pending |
| Phase 3 | Backtest Sharpe > 0.5 | ⏳ Pending |
| Phase 4 | Agent response time < 5 sec | ⏳ Pending |
| Phase 5 | 10 test orders filled correctly | ⏳ Pending |
| Phase 6 | Full pipeline runs twice daily | ⏳ Pending |
| Phase 7 | All unit + integration tests passing | ⏳ Pending |
| Phase 8 | 4 weeks stable paper trading | ⏳ Pending |

---

## One-Sentence Summaries

- **ML Engine:** XGBoost generates BUY/SELL signals (only source of trades).
- **Agents:** Ollama critiques decisions (reduce/veto only).
- **Risk:** Hard rules enforce discipline (no overrides).
- **Execution:** Alpaca submits orders, tracks fills.
- **Monitoring:** Twice daily runs + intraday emergency rules.
- **Audit:** Every decision logged, fully queryable.
- **Deployment:** Docker Compose (reproducible, portable).

---

## You Are Here 🟢

```
Design Phase: ✅ COMPLETE
└─ Next: Phase 1 (Infrastructure)
   └─ When ready: Come back and say
      "I'm ready to start Phase 1"
```

---

**Bookmark this page. It's your single-page visual summary.**

All details in the other docs. This is your cheat sheet.

