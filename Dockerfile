FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements FIRST (cached layer)
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Copy application code AFTER (won't invalidate pip cache if only code changes)
COPY src ./src
COPY config ./config
COPY scripts ./scripts
COPY db ./db
COPY tests ./tests

# Keep container alive for interactive dev; override in compose if needed
CMD ["sleep", "infinity"]


