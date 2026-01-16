"""Common Database Queries."""


def get_ohlcv(ticker, start_date, end_date):
    """Get OHLCV bars for a ticker."""
    pass


def store_ohlcv(ticker, date, open_, high, low, close, volume):
    """Store OHLCV bar."""
    pass


def get_features(ticker, date):
    """Get features for a ticker on a date."""
    pass


def get_all_positions():
    """Get all open positions."""
    pass


def get_position(ticker):
    """Get position for a ticker."""
    pass


def get_portfolio_state():
    """Get current portfolio state."""
    pass
