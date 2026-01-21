"""Structured Logging - JSON format with file and console output."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def setup_logging(config: Dict[str, Any] = None) -> logging.Logger:
    """
    Setup structured JSON logging with file and console handlers.
    
    Args:
        config: Logging configuration dict with keys:
            - level: Log level (DEBUG, INFO, WARNING, ERROR)
            - file: Log file path
            - format: 'json' or 'text'
            - max_size_mb: Max log file size before rotation
            - backup_count: Number of backup files to keep
    
    Returns:
        Configured logger instance
    """
    config = config or {}
    log_level = config.get('level', 'INFO')
    log_file = config.get('file', 'logs/market_trader.log')
    log_format = config.get('format', 'json')
    
    # Create logs directory if needed
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('market_trader')
    logger.setLevel(getattr(logging, log_level.upper()))
    logger.handlers.clear()
    
    # JSON formatter
    if log_format == 'json':
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    max_bytes = config.get('max_size_mb', 100) * 1024 * 1024
    backup_count = config.get('backup_count', 10)
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Wrapper for structured logging with domain-specific methods.
    Provides convenient methods for logging trading events.
    """
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger('market_trader')
    
    def _log_with_data(self, level: str, message: str, **kwargs):
        """Log message with extra structured data."""
        extra_data = {k: v for k, v in kwargs.items() if v is not None}
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra={'extra_data': extra_data})
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self._log_with_data('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self._log_with_data('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with structured data."""
        self._log_with_data('ERROR', message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self._log_with_data('DEBUG', message, **kwargs)
    
    # Domain-specific logging methods
    
    def log_signal(self, ticker: str, signal: str, confidence: float, **kwargs):
        """Log ML signal generation."""
        self.info(
            f"ML Signal: {signal} {ticker}",
            ticker=ticker,
            signal=signal,
            confidence=confidence,
            event_type='ml_signal',
            **kwargs
        )
    
    def log_agent_critique(self, agent: str, ticker: str, recommendation: str, **kwargs):
        """Log agent critique."""
        self.info(
            f"Agent {agent}: {recommendation} for {ticker}",
            agent=agent,
            ticker=ticker,
            recommendation=recommendation,
            event_type='agent_critique',
            **kwargs
        )
    
    def log_risk_decision(self, ticker: str, decision: str, **kwargs):
        """Log risk controller decision."""
        self.info(
            f"Risk Decision: {decision} for {ticker}",
            ticker=ticker,
            decision=decision,
            event_type='risk_decision',
            **kwargs
        )
    
    def log_trade(self, ticker: str, side: str, quantity: int, price: float, **kwargs):
        """Log trade execution."""
        self.info(
            f"Trade Executed: {side} {quantity} {ticker} @ ${price:.2f}",
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            event_type='trade_execution',
            **kwargs
        )
    
    def log_portfolio_state(self, total_value: float, cash: float, num_positions: int, **kwargs):
        """Log portfolio state snapshot."""
        self.info(
            f"Portfolio: ${total_value:,.2f} ({num_positions} positions)",
            total_value=total_value,
            cash=cash,
            num_positions=num_positions,
            event_type='portfolio_state',
            **kwargs
        )
    
    def log_pipeline_start(self, pipeline_type: str):
        """Log pipeline execution start."""
        self.info(
            f"Pipeline started: {pipeline_type}",
            pipeline_type=pipeline_type,
            event_type='pipeline_start'
        )
    
    def log_pipeline_complete(self, pipeline_type: str, duration_seconds: float, **kwargs):
        """Log pipeline execution completion."""
        self.info(
            f"Pipeline completed: {pipeline_type} ({duration_seconds:.2f}s)",
            pipeline_type=pipeline_type,
            duration_seconds=duration_seconds,
            event_type='pipeline_complete',
            **kwargs
        )
    
    def log_error_with_context(self, component: str, error_msg: str, **kwargs):
        """Log error with component context."""
        self.error(
            f"Error in {component}: {error_msg}",
            component=component,
            error_message=error_msg,
            event_type='error',
            **kwargs
        )
