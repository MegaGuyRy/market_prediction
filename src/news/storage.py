"""News Storage Module - pgvector storage interface."""


def store_news(title, content, embedding, sentiment):
    """Store news + embedding in PostgreSQL pgvector."""
    pass


def get_stored_news(ticker, limit=10):
    """Retrieve stored news for a ticker."""
    pass
