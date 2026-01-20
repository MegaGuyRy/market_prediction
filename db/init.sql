-- Enable pgvector for embeddings and similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- MARKET DATA
-- ============================================================================

-- Daily price bars (OHLCV source of truth)
CREATE TABLE IF NOT EXISTS ohlcv (
  ticker      TEXT NOT NULL,
  date        DATE NOT NULL,
  open        NUMERIC NOT NULL,
  high        NUMERIC NOT NULL,
  low         NUMERIC NOT NULL,
  close       NUMERIC NOT NULL,
  adj_close   NUMERIC,
  volume      BIGINT NOT NULL,
  source      TEXT DEFAULT 'alpaca',
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_date ON ohlcv(date);
CREATE INDEX IF NOT EXISTS idx_ohlcv_ticker ON ohlcv(ticker);

-- ============================================================================
-- FEATURES
-- ============================================================================

-- Engineered features for ML
CREATE TABLE IF NOT EXISTS features (
  id          SERIAL PRIMARY KEY,
  ticker      TEXT NOT NULL,
  date        DATE NOT NULL,
  feature_set JSONB NOT NULL,  -- All features as JSON (technical, sentiment, etc)
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_features_ticker_date ON features(ticker, date);

-- ============================================================================
-- NEWS
-- ============================================================================

-- News articles with embeddings for RAG
CREATE TABLE IF NOT EXISTS news (
  id              SERIAL PRIMARY KEY,
  headline        TEXT NOT NULL,
  content         TEXT,
  source          TEXT NOT NULL,
  url             TEXT,
  published_at    TIMESTAMPTZ NOT NULL,
  sentiment_score NUMERIC,  -- -1 (bearish) to +1 (bullish)
  embedding       vector(768),  -- LLM embeddings for similarity search
  tickers         TEXT[],  -- Related tickers mentioned
  ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_tickers ON news USING GIN(tickers);
-- HNSW index for fast vector similarity search
CREATE INDEX IF NOT EXISTS idx_news_embedding ON news USING hnsw (embedding vector_cosine_ops);

-- ============================================================================
-- ML SIGNALS
-- ============================================================================

-- ML model predictions
CREATE TABLE IF NOT EXISTS signals (
  id            SERIAL PRIMARY KEY,
  ticker        TEXT NOT NULL,
  signal_date   DATE NOT NULL,
  model_version INTEGER NOT NULL,
  signal        TEXT NOT NULL CHECK (signal IN ('BUY', 'SELL', 'HOLD')),
  confidence    NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  expected_return NUMERIC,
  edge_score    NUMERIC,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker_date ON signals(ticker, signal_date);
CREATE INDEX IF NOT EXISTS idx_signals_date ON signals(signal_date);

-- ============================================================================
-- AGENT CRITIQUES
-- ============================================================================

-- LLM agent critiques of ML signals
CREATE TABLE IF NOT EXISTS agent_critiques (
  id             SERIAL PRIMARY KEY,
  signal_id      INTEGER REFERENCES signals(id),
  agent_name     TEXT NOT NULL,  -- analyst, bull, bear, risk, committee
  recommendation TEXT NOT NULL CHECK (recommendation IN ('APPROVE', 'VETO', 'REDUCE')),
  rationale      TEXT,
  context_json   JSONB,  -- Additional context from agent
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_critiques_signal ON agent_critiques(signal_id);

-- ============================================================================
-- RISK DECISIONS
-- ============================================================================

-- Risk controller final decisions
CREATE TABLE IF NOT EXISTS risk_decisions (
  id              SERIAL PRIMARY KEY,
  signal_id       INTEGER REFERENCES signals(id),
  decision        TEXT NOT NULL CHECK (decision IN ('APPROVE', 'REJECT')),
  sized_quantity  INTEGER,
  stop_price      NUMERIC,
  target_price    NUMERIC,
  risk_amount     NUMERIC,  -- Dollar risk per trade
  reject_reason   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_decisions_signal ON risk_decisions(signal_id);

-- ============================================================================
-- EXECUTION
-- ============================================================================

-- Orders submitted to broker
CREATE TABLE IF NOT EXISTS orders (
  id             SERIAL PRIMARY KEY,
  signal_id      INTEGER REFERENCES signals(id),
  ticker         TEXT NOT NULL,
  order_type     TEXT NOT NULL,  -- market, limit, stop
  side           TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
  quantity       INTEGER NOT NULL,
  limit_price    NUMERIC,
  stop_price     NUMERIC,
  broker_order_id TEXT,
  status         TEXT NOT NULL,  -- pending, filled, cancelled, rejected
  submitted_at   TIMESTAMPTZ DEFAULT NOW(),
  filled_at      TIMESTAMPTZ,
  fill_price     NUMERIC,
  fill_quantity  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_orders_ticker ON orders(ticker);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_submitted ON orders(submitted_at);

-- Filled trades
CREATE TABLE IF NOT EXISTS trades (
  id          SERIAL PRIMARY KEY,
  order_id    INTEGER REFERENCES orders(id),
  ticker      TEXT NOT NULL,
  side        TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
  quantity    INTEGER NOT NULL,
  price       NUMERIC NOT NULL,
  commission  NUMERIC DEFAULT 0,
  executed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
CREATE INDEX IF NOT EXISTS idx_trades_executed ON trades(executed_at);

-- ============================================================================
-- PORTFOLIO
-- ============================================================================

-- Current open positions
CREATE TABLE IF NOT EXISTS positions (
  id              SERIAL PRIMARY KEY,
  ticker          TEXT NOT NULL UNIQUE,
  quantity        INTEGER NOT NULL,
  avg_entry_price NUMERIC NOT NULL,
  current_price   NUMERIC,
  unrealized_pnl  NUMERIC,
  stop_price      NUMERIC,
  target_price    NUMERIC,
  opened_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_ticker ON positions(ticker);

-- Portfolio state snapshots
CREATE TABLE IF NOT EXISTS portfolio_state (
  id                  SERIAL PRIMARY KEY,
  timestamp           TIMESTAMPTZ DEFAULT NOW(),
  total_value         NUMERIC NOT NULL,
  cash                NUMERIC NOT NULL,
  positions_value     NUMERIC NOT NULL,
  unrealized_pnl      NUMERIC,
  unrealized_pnl_pct  NUMERIC,
  daily_drawdown      NUMERIC,
  max_daily_drawdown  NUMERIC,
  num_positions       INTEGER,
  max_exposure        NUMERIC,  -- % of account in positions
  snapshot_json       JSONB
);

CREATE INDEX IF NOT EXISTS idx_portfolio_state_timestamp ON portfolio_state(timestamp DESC);

-- ============================================================================
-- AUDIT & LOGGING
-- ============================================================================

-- Immutable audit trail (all decision events)
CREATE TABLE IF NOT EXISTS audit_log (
  id             SERIAL PRIMARY KEY,
  timestamp      TIMESTAMPTZ DEFAULT NOW(),
  event_type     TEXT NOT NULL,  -- signal_generated, agent_critique, risk_decision, order_submitted, etc
  component      TEXT NOT NULL,  -- ml, agents, risk, execution
  ticker         TEXT,
  event_data     JSONB NOT NULL,  -- Full event details
  trace_id       TEXT,  -- Links all events for one decision chain
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_trace_id ON audit_log(trace_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_ticker ON audit_log(ticker);

-- ============================================================================
-- ML MODELS
-- ============================================================================

-- ML model versions and metadata
CREATE TABLE IF NOT EXISTS model_versions (
  id                  SERIAL PRIMARY KEY,
  model_type          TEXT NOT NULL,  -- xgboost, lstm, etc
  version             TEXT NOT NULL UNIQUE,
  training_date       DATE NOT NULL,
  training_start_date DATE NOT NULL,
  training_end_date   DATE NOT NULL,
  hyperparameters     JSONB,
  backtest_metrics    JSONB,  -- sharpe, drawdown, win_rate, etc
  artifact_path       TEXT,
  is_active           BOOLEAN DEFAULT FALSE,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_versions_active ON model_versions(is_active) WHERE is_active = TRUE;
