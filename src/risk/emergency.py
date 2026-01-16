"""Emergency Rules - drawdown enforcement, volatility rules."""


def check_soft_drawdown_limit(portfolio_state):
    """Check 2% soft limit (alert, monitor)."""
    pass


def check_hard_drawdown_limit(portfolio_state):
    """Check 3% hard limit (emergency de-risk)."""
    pass


def execute_emergency_de_risk():
    """Reduce all positions by 50% on 3% drawdown breach."""
    pass


def check_gap_volatility_rules(current_price, last_close):
    """Check for large gaps or volatility spikes."""
    pass
