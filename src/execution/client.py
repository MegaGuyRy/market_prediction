"""Alpaca API Client Wrapper."""


class AlpacaClient:
    """Wrapper for Alpaca API (paper trading)."""
    
    def __init__(self, api_key, api_secret, paper=True):
        self.paper = paper
        self.account = None
    
    def get_account(self):
        """Get account info."""
        pass
    
    def get_positions(self):
        """Get all positions."""
        pass
    
    def get_price(self, ticker):
        """Get current price."""
        pass
    
    def submit_order(self, ticker, qty, side, order_type='market'):
        """Submit order to Alpaca."""
        pass
    
    def cancel_order(self, order_id):
        """Cancel an order."""
        pass
    
    def get_fills(self):
        """Get recent fills."""
        pass
