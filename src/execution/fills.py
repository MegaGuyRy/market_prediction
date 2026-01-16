"""Fill Tracking and Reconciliation."""


def track_fill(order_id, ticker, qty, fill_price, fill_time):
    """Record a fill in database."""
    pass


def reconcile_fills():
    """Reconcile fills between Alpaca and local database."""
    pass


def calculate_pnl(position, current_price):
    """Calculate unrealized PnL for a position."""
    pass


def record_closed_trade(position, exit_price, exit_time):
    """Record a closed trade with PnL."""
    pass
