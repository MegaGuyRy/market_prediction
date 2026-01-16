"""OHLCV Data Fetch Module - Market data from Alpaca + Yahoo."""


def fetch_alpaca_bars(ticker, start_date, end_date):
    """Fetch OHLCV bars from Alpaca API."""
    pass


def fetch_yahoo_bars(ticker, start_date, end_date):
    """Fetch OHLCV bars from Yahoo Finance (backup)."""
    pass


def fetch_bars(ticker, start_date, end_date, source='alpaca'):
    """Unified interface to fetch bars with fallback."""
    pass
