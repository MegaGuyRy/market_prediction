"""Structured Logging - JSON format."""

import json
from datetime import datetime


class StructuredLogger:
    """Logger that outputs structured JSON."""
    
    def log_event(self, event_type, component, data):
        """Log an event as JSON."""
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'component': component,
            'data': data
        }
        print(json.dumps(event))
    
    def log_signal(self, ticker, signal, confidence):
        """Log a signal."""
        pass
    
    def log_trade(self, ticker, action, qty, price):
        """Log a trade."""
        pass
    
    def log_error(self, component, error_msg):
        """Log an error."""
        pass
