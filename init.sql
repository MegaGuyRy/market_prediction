-- SQL script to initialize the database schema for storing daily price bars
-- Daily price bars (source of truth)
CREATE TABLE IF NOT EXISTS price_bars_daily (
  symbol      TEXT NOT NULL,
  date        DATE NOT NULL,
  open        NUMERIC,
  high        NUMERIC,
  low         NUMERIC,
  close       NUMERIC,
  adj_close   NUMERIC,
  volume      BIGINT,
  source      TEXT DEFAULT 'yahoo',
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (symbol, date)
);

-- Helpful index for time-based queries
CREATE INDEX IF NOT EXISTS idx_price_bars_daily_date ON price_bars_daily(date);
