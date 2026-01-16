# Implementation Roadmap – v1 Build Plan

**Timeline:** 6–8 weeks  
**Status:** Design phase complete, ready for engineering

---

## Phase 1: Infrastructure & Foundations (Week 1–2)

### Goals
- Docker + Docker Compose fully configured
- PostgreSQL + pgvector initialized
- Ollama running with Mistral 7B
- Development environment ready
- All components can communicate

### Deliverables
- [ ] `docker-compose.yml` with all services
- [ ] `schema.sql` with all tables
- [ ] Ollama model loaded and tested
- [ ] Config files (settings.yaml, models.yaml, agents.yaml, risk_rules.yaml)
- [ ] Database connection pool working
- [ ] Basic logging framework

### Success Criteria
- `docker-compose up` fully starts system
- PostgreSQL accessible from app container
- Ollama responds to test inference
- All configs load without errors

---

## Phase 2: Data Layer (Week 2–3)

### Goals
- News ingestion pipeline working
- Market data (OHLCV) fetching consistently
- Feature engineering pipeline building features
- All data stored and queryable in PostgreSQL

### Deliverables
- [ ] `src/news/` module (fetcher, parser, embedder, storage, RAG)
- [ ] `src/data/` module (OHLCV fetch from Alpaca + Yahoo)
- [ ] `src/features/` module (technical indicators, sentiment, scaling)
- [ ] Feature store query interface
- [ ] Unit tests for data pipelines

### Success Criteria
- Pull last 30 days of S&P 100 OHLCV
- Embed news headlines and store in pgvector
- Generate features for 10 random tickers
- Query features by ticker + date range

---

## Phase 3: ML Pipeline (Week 3–4)

### Goals
- XGBoost model training pipeline working
- Model can generate BUY/SELL/HOLD signals
- Backtesting framework validates signals
- Model versioning and persistence

### Deliverables
- [ ] `src/ml/training.py` (XGBoost training, hyperparameter tuning)
- [ ] `src/ml/inference.py` (load model, generate signals)
- [ ] `src/ml/backtest.py` (historical simulation, metrics)
- [ ] Model artifact storage (versioning)
- [ ] Unit + integration tests

### Success Criteria
- Train model on 2+ years historical data
- Backtest shows positive Sharpe (>0.5)
- Generate signals for 50 candidates
- Model can be loaded and re-used

---

## Phase 4: Agent System (Week 4–5)

### Goals
- LLM agents critiquing ML proposals
- Structured JSON responses reliable
- Agent decision flow orchestrated
- Critique stored and queryable

### Deliverables
- [ ] `src/agents/` module (base, analyst, bull, bear, risk, committee)
- [ ] `src/agents/llm_interface.py` (Ollama integration)
- [ ] Prompt engineering for each agent role
- [ ] JSON response parsing and validation
- [ ] Unit + integration tests

### Success Criteria
- Each agent responds with valid JSON
- Committee provides veto recommendations
- Critique latency < 5 sec per ticker
- 100+ agent critiques logged and queryable

---

## Phase 5: Risk & Execution (Week 5–6)

### Goals
- Risk controller enforcing all hard rules
- Position sizing correct
- Alpaca API integration working
- Orders submitted and filled tracked

### Deliverables
- [ ] `src/risk/controller.py` (main orchestrator)
- [ ] `src/risk/sizing.py` (position sizing logic)
- [ ] `src/risk/constraints.py` (portfolio limits)
- [ ] `src/risk/stops.py` (stop/target calculation)
- [ ] `src/risk/emergency.py` (drawdown enforcement)
- [ ] `src/execution/client.py` (Alpaca API wrapper)
- [ ] `src/execution/orders.py` (order submission)
- [ ] `src/execution/fills.py` (fill tracking)
- [ ] Unit tests

### Success Criteria
- Risk controller correctly sizes 100 positions
- Constraints enforced (10-15 max, 0.5% per trade, 3% drawdown)
- Submit 10 test orders to Alpaca paper
- Track fills, PnL, costs accurately

---

## Phase 6: Orchestration & Monitoring (Week 6–7)

### Goals
- Full twice-daily orchestration working
- Intraday monitoring running
- Audit logging complete and queryable
- All components coordinating

### Deliverables
- [ ] `src/scheduler/orchestrator.py` (twice-daily run)
- [ ] `src/scheduler/state.py` (portfolio state)
- [ ] `src/scheduler/intraday.py` (15–30 min monitoring)
- [ ] `src/utils/logging.py` (structured audit logs)
- [ ] Cron jobs or scheduler configuration
- [ ] Integration tests

### Success Criteria
- Run full pipeline: news → candidates → ML → agents → risk → execution
- Intraday stops fire correctly
- Every decision logged to PostgreSQL
- Query audit trail for any trade

---

## Phase 7: Testing & Validation (Week 7–8)

### Goals
- Comprehensive test suite passing
- End-to-end scenarios validated
- Backtesting confirms profitability
- Ready for paper trading

### Deliverables
- [ ] Unit test suite (20+ tests)
- [ ] Integration test suite (10+ tests)
- [ ] End-to-end scenarios (5+ scenarios)
- [ ] Backtest results (2+ years data)
- [ ] Documentation (architecture, API, deployment)

### Success Criteria
- All tests passing locally
- Backtest Sharpe > 0.5
- No audit trail gaps
- Docker Compose fully reproducible
- Ready for 4-week paper trading

---

## Phase 8: Paper Trading & Documentation (Week 8+)

### Goals
- Full system running live in paper mode
- Monitoring and alerting working
- Documentation complete
- Ready for production deployment

### Deliverables
- [ ] Live paper trading for 4 weeks
- [ ] Monitoring dashboard / logs
- [ ] Deployment guide
- [ ] Operations runbook
- [ ] Performance analysis

### Success Criteria
- 4 weeks of stable paper trading
- No critical errors or missed audits
- Consistent execution quality
- Confidence to scale to live trading

---

## Dependencies & Blockers

### Critical Path
1. Docker + DB (blocks everything)
2. Data layer (blocks ML)
3. ML pipeline (blocks agents)
4. Agents (blocks risk controller)
5. Execution (blocks orchestrator)
6. Orchestrator (blocks paper trading)

### Key Risks
- Ollama latency (agent throughput bottleneck)
- Alpaca API rate limits (order submission)
- News source reliability (depends on RSS feeds)
- Feature engineering complexity (overfitting risk)

### Mitigation
- Profile Ollama latency early (Phase 1)
- Use Alpaca sandbox aggressively (Phase 5)
- Curate news sources (Phase 2)
- Validate features on historical data (Phase 3)

---

## Team Responsibilities (Solo Build)

**You:** All phases

**Automation:** After v1, consider:
- Scheduled retraining (cron or APScheduler)
- Daily run orchestration (APScheduler or custom scheduler)
- Alert notifications (Slack integration)

---

## Milestones

| Milestone | Completion | Criteria |
|-----------|-----------|----------|
| **Infrastructure Ready** | End of Week 2 | Docker working, DB initialized, Ollama running |
| **Data Pipeline Live** | End of Week 3 | News + OHLCV flowing, features generated |
| **ML Validated** | End of Week 4 | Model trained, backtests positive, signals generated |
| **Agents Critiquing** | End of Week 5 | Agent system responding, critiques logged |
| **Execution Ready** | End of Week 6 | Test orders submitted, filled, tracked |
| **Orchestration Complete** | End of Week 7 | Full pipeline running twice daily |
| **Tests Passing** | End of Week 7 | Unit + integration tests green |
| **Paper Trading Starts** | Start of Week 8 | 4-week validation run begins |
| **v1 Complete** | Week 12 | 4-week paper trading validation done |

---

## How to Use This Roadmap

1. **Print this document** (or keep it open in a second window)
2. **Work through phases sequentially** (don't skip ahead)
3. **At end of each phase:** commit to git, update this document with dates
4. **If blocked:** pause phase, resolve blocker, then resume
5. **After Phase 7:** switch to paper trading mode and monitor daily

---

## Next Steps

1. ✅ Design decisions locked (this is done)
2. ⏭️ **Start Phase 1:** Setup Docker + DB + Ollama (next session)

