"""Backtesting Framework."""


def run_backtest(start_date, end_date, initial_capital=100000):
    """
    Run full backtest on historical data.
    
    Returns: {
        'returns': float,
        'sharpe': float,
        'max_drawdown': float,
        'win_rate': float,
        'trades': list
    }
    """
    pass


def compute_metrics(pnl_series):
    """Compute backtest metrics (Sharpe, DD, etc)."""
    pass
