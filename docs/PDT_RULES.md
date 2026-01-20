# Pattern Day Trader (PDT) Rules & Workarounds

**Purpose:** Document FINRA PDT rules and implementation strategy for staying compliant while maximizing trading opportunities.

---

## FINRA PDT Definition

### What is a Day Trade?

A **day trade** is defined as a round-trip pair of trades within the same day (including extended hours):

- **Long positions:** Buy and then sell same security, same calendar day
- **Short positions:** Sell short and cover short, same calendar day
- **Definition:** Initial opening transaction + subsequent closing transaction = 1 day trade

**Important:** Day trades are counted regardless of:
- Share quantity (1 share = 1 day trade)
- Frequency (multiple round-trips = multiple day trades)
- Time between opening and closing (5 min or 5 hours, still 1 day trade)

### PDT Account Flag Criteria

An account is designated as **Pattern Day Trader** (PDT) if BOTH conditions are met:

1. **4 or more day trades** within any 5 business days, AND
2. **Day trades represent >6% of total trades** within the same 5-day window

**Example Scenarios:**

| Scenario | Day Trades in 5 Days | Total Trades in 5 Days | 6% Threshold | PDT? |
|----------|:---:|:---:|:---:|:---:|
| Normal trader | 3 | 50 | 3 (6% of 50) | ❌ No |
| Active trader | 4 | 50 | 3 (6% of 50) | ✅ Yes (4 ≥ 4 AND 4 > 3) |
| High volume | 5 | 100 | 6 (6% of 100) | ✅ Yes (5 ≥ 4 AND 5 < 6, borderline) |
| Safe trader | 4 | 100 | 6 (6% of 100) | ❌ No (4 ≥ 4 BUT 4 < 6) |

### Consequences of PDT Flag

Once flagged as PDT:

1. **Minimum equity requirement:** $25,000 account balance required
2. **Margin restrictions:** Day trading buying power = 4× maintenance margin excess
3. **Liquidation:** If equity drops below $25K, account becomes restricted
4. **Trading halt:** Cannot day trade until equity restored to $25K+ or PDT flag removed

### Cryptocurrency Exception

**Crypto is NOT subject to PDT rules:**
- Round-trip crypto trades on the same day do NOT count toward day trade count
- Crypto orders are NOT evaluated by PDT protection logic
- Can day trade crypto freely (from PDT perspective)

---

## Implementation Strategy: Avoid/Manage PDT

### Option 1: Strict PDT Avoidance (Recommended for v1)

**Rule:** Never execute day trades (round-trips same day)

**Implementation:**
- Track every entry price and date per ticker
- Only exit on DIFFERENT calendar day from entry
- Enforce in `risk/controller.py`: reject any SELL if ticker entered same day

**Benefits:**
- 100% PDT-safe
- Simple logic
- Conservative risk management
- Aligns with swing-trading philosophy

**Drawbacks:**
- Can't capitalize on same-day reversals
- May miss quick profits
- Longer holding periods increase overnight gap risk

### Option 2: Position Hold Windows (Swing Trading)

**Rule:** Hold every position minimum 1 business day

**Implementation:**
- Track entry date for each position
- Only allow exit if `current_date > entry_date`
- Intraday monitoring: close emergency stops/drawdowns (don't count as day trades if opened/closed same day with no re-entry)

**Benefits:**
- Flexible timing
- Can exit at optimal price (next day)
- Reduces emotional/reactive trading
- Natural swing-trading rhythm

**Drawbacks:**
- Overnight gap risk
- Still subject to market shocks
- Requires stop-loss discipline

### Option 3: Multi-Account Strategy (Requires $50K+ capital)

**Rule:** Spread trading across 2+ accounts to distribute day trades

**Example:**
- Account A: $25K, max 3 day trades per 5 days (safe)
- Account B: $25K, max 3 day trades per 5 days (safe)
- Total capacity: 6 day trades / 5 days (within PDT limits for both)

**Implementation:**
- Track day trades per account separately
- Route orders based on account utilization
- Requires multiple Alpaca paper/live accounts

**Benefits:**
- Can day trade strategically
- Spreads risk
- Maximizes available trading capital

**Drawbacks:**
- Requires 2× capital
- Complex order routing
- Administrative overhead

### Option 4: Hybrid: Swing + Crypto

**Rule:** 
- Equities: Hold ≥1 business day (swing trading, PDT-safe)
- Crypto: Day trade freely (no PDT rules)

**Implementation:**
- Route BUY/SELL signals:
  - If `signal_ticker` in crypto_universe → allow same-day round-trips
  - If `signal_ticker` in equity_universe → enforce hold-until-next-day rule

**Benefits:**
- Leverages crypto exemption
- Captures both crypto alpha + equity swing returns
- PDT-safe
- Flexible for crypto volatility

**Drawbacks:**
- Adds crypto execution complexity
- Requires crypto data/feeds
- Alpaca doesn't support crypto in paper mode (fallback needed)

---

## v1 Recommendation: Option 1 (Strict Avoidance)

**Why:**
1. Simplest to implement
2. Robust (zero PDT risk)
3. Aligns with institutional swing-trading best practices
4. Forces disciplined, planned exits
5. Reduces overtrading

**Implementation in Code:**

```python
# src/risk/controller.py
def validate_exit_signal(ticker, signal, entry_date):
    """
    Enforce no-day-trade rule: only allow SELL if ticker 
    was NOT entered same calendar day.
    """
    current_date = get_market_date()  # Today in ET
    
    if signal == "SELL":
        if entry_date == current_date:
            return {
                "approved": False,
                "reason": "PDT rule: Cannot exit same-day entry",
                "next_allowed_exit": add_trading_days(entry_date, 1)
            }
    
    return {"approved": True}

# src/risk/controller.py - in main sizing logic
def can_execute_trade(ticker, signal, positions):
    """Main decision point for all trades."""
    
    # Check PDT for SELL signals
    if signal == "SELL" and ticker in positions:
        pdt_check = validate_exit_signal(
            ticker, 
            signal, 
            positions[ticker]["entry_date"]
        )
        
        if not pdt_check["approved"]:
            return {
                "decision": "REJECT",
                "reason": pdt_check["reason"]
            }
    
    # ... continue with other checks
```

**Database Tracking:**

```sql
-- In positions table, track entry date
ALTER TABLE positions ADD COLUMN entry_date DATE;

-- In audit_log, track all trades
-- Entry: event_type='POSITION_OPENED', entry_date=today
-- Exit: event_type='POSITION_CLOSED', entry_date=queried from positions
```

---

## Future (v1.1+): Multi-Account or Crypto Strategy

Once operational, consider implementing:

1. **Day trade counter:** Track rolling 5-day window
   ```sql
   CREATE TABLE day_trades (
     id SERIAL PRIMARY KEY,
     trade_date DATE,
     ticker TEXT,
     entry_time TIMESTAMP,
     exit_time TIMESTAMP,
     is_day_trade BOOLEAN,  -- true if same-day round-trip
     account_id TEXT,
     created_at TIMESTAMP
   );
   ```

2. **PDT status monitoring:** Alert when approaching 4 day trades
   ```python
   def check_pdt_status(account_id, lookback_days=5):
       day_trades = query_day_trades(account_id, lookback_days)
       total_trades = query_all_trades(account_id, lookback_days)
       
       if len(day_trades) >= 4 and len(day_trades) / len(total_trades) > 0.06:
           return "PDT_FLAGGED"
       return "SAFE"
   ```

3. **Multi-account routing:** Distribute trades across accounts

4. **Crypto signals:** Route crypto signals to separate execution path

---

## References

- FINRA Rule 4520: https://www.finra.org/rules-guidance/rulebooks/finra-rules/4520
- SEC: https://www.sec.gov/cgi-bin/browse-edgar
- Alpaca PDT Rules: https://alpaca.markets/docs/trading/margin-margin-multiplier

---

## Checklist: v1 Implementation

- [ ] Add `entry_date` column to `positions` table
- [ ] Add PDT validation to `risk/controller.py`
- [ ] Log all entry/exit trades to `audit_log`
- [ ] Create test cases: validate no same-day exits
- [ ] Document in risk_rules.yaml
- [ ] Alert user if position entered today (can't exit today)
