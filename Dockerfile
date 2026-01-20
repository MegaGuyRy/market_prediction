FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# Copy source and configs
COPY src ./src
COPY docs ./docs
COPY config ./config
COPY db ./db
COPY tests ./tests

# Keep container alive for interactive dev; override in compose if needed
CMD ["sleep", "infinity"]


