FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    python -m pip show pandas


# Copy code
COPY pipeline ./pipeline
COPY configs ./configs

# Default command (override in docker compose run)
CMD ["python"]


