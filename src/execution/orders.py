"""Order Management - submission and tracking."""


def submit_order(ticker, qty, side, stop_loss=None, target=None):
    """Submit market order to Alpaca."""
    pass


def submit_orders_batch(orders_list):
    """Submit multiple orders."""
    pass


def get_order_status(order_id):
    """Get current order status."""
    pass


def wait_for_fill(order_id, timeout=60):
    """Wait for order to fill."""
    pass
