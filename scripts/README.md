# Scripts Directory

This directory contains operational scripts, utilities, and organized test/debug code for the market prediction system.

## Directory Structure

```
scripts/
├── run_full_pipeline.py    # Main pipeline orchestrator (START HERE)
├── bootstrap_prices.py      # Historical price data loader
├── tests/                   # Testing scripts
└── debug/                   # Debug and comparison scripts
```

## Main Scripts

### 🚀 run_full_pipeline.py
**Primary pipeline orchestrator** - Runs the complete news ingestion and processing pipeline.

**What it does:**
1. **Fetcher**: Collects news from RSS feeds (Yahoo Finance, SEC, Reuters)
2. **Parser**: Extracts sentiment scores using FinBERT
3. **Embedder**: Generates 768-dimensional semantic embeddings
4. **Storage**: Stores news in PostgreSQL with pgvector
5. **RAG**: Demonstrates retrieval and ticker sentiment analysis

**Usage:**
```bash
# Default: Fetch last 24 hours of news
python scripts/run_full_pipeline.py

# Fetch last 48 hours
python scripts/run_full_pipeline.py --hours 48

# Fetch last week
python scripts/run_full_pipeline.py --hours 168
```

**Features:**
- ✅ Full pipeline validation
- ✅ Semantic search demonstration
- ✅ Ticker sentiment aggregation
- ✅ Sector analysis
- ✅ Sample data fallback if no news available
- ✅ Detailed progress reporting

**Prerequisites:**
- PostgreSQL running on localhost:5433
- Virtual environment activated
- Dependencies installed

---

### 📊 bootstrap_prices.py
**Historical price data loader** - Fetches OHLCV data from Yahoo Finance.

**What it does:**
- Downloads historical stock prices from Yahoo Finance
- Stores data in PostgreSQL `ohlcv` table
- Supports batch loading for multiple symbols
- Handles missing data gracefully

**Usage:**
```bash
python scripts/bootstrap_prices.py
```

**Data Source:**
- Reads tickers from `configs/universe.csv`
- Fetches from 2015-01-01 to present
- Uses upsert logic (no duplicates)

---

## Test Scripts (`tests/`)

Organized testing scripts for validating different components:

### test_integration.py
Tests core infrastructure components:
- Database connectivity
- Ollama API connectivity
- Config loading
- Logging functionality

### test_news_pipeline.py
End-to-end news pipeline testing with detailed component validation.

### test_rag.py
RAG (Retrieval-Augmented Generation) functionality tests.

### test_sentiment_methods.py
Compares different sentiment analysis approaches (FinBERT, VADER, etc.).

### test_ticker_extraction.py
Validates ticker extraction from news text.

### validate_phase2.py
Phase 2 completion validation checklist.

**Run tests:**
```bash
python scripts/tests/test_integration.py
python scripts/tests/test_news_pipeline.py
```

---

## Debug Scripts (`debug/`)

Tools for debugging and comparing different implementation approaches:

### compare_ticker_extraction.py
Compares different ticker extraction methods:
- NLP/NER (spaCy)
- LLM-based (Ollama)
- Hybrid approaches

### debug_finbert.py
Debug and validate FinBERT sentiment model loading and inference.

**Run debug scripts:**
```bash
python scripts/debug/compare_ticker_extraction.py
python scripts/debug/debug_finbert.py
```

---

## Quick Start

### 1️⃣ First Time Setup
```bash
# Activate virtual environment
source .venv/bin/activate

# Ensure database is running
docker-compose up -d postgres

# Bootstrap historical prices (optional)
python scripts/bootstrap_prices.py
```

### 2️⃣ Run the Pipeline
```bash
# Run complete news pipeline
python scripts/run_full_pipeline.py
```

### 3️⃣ Validate System
```bash
# Test infrastructure
python scripts/tests/test_integration.py

# Test news components
python scripts/tests/test_news_pipeline.py
```

---

## Environment Requirements

**Database:**
- PostgreSQL 14+ with pgvector extension
- Running on `localhost:5433` (or configure in `settings.yaml`)

**Python Environment:**
- Python 3.10+
- Virtual environment with all dependencies installed
- See `requirements.txt` for full package list

**Optional Services:**
- Ollama (for LLM-based ticker extraction)
- If unavailable, system falls back to keyword mapping

---

## Pipeline Output

The pipeline produces:

1. **Database Records**
   - News articles in `news` table
   - Embeddings stored as pgvector types
   - Ticker associations in JSONB

2. **Console Reports**
   - Fetched article count
   - Sentiment distribution
   - Ticker analysis
   - Semantic search results

3. **Logs**
   - Structured JSON logs in `logs/` directory
   - Detailed component execution traces

---

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart if needed
docker-compose restart postgres
```

### No News Fetched
The pipeline will create sample test data automatically. RSS feeds may be temporarily unavailable or rate-limited.

### Ollama Not Available
System automatically falls back to keyword-based ticker extraction. This is normal if Ollama service is not running.

### Import Errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

## Development Notes

### Adding New Scripts

**Operational scripts** → Place in `scripts/` root
**Test scripts** → Place in `scripts/tests/`
**Debug/comparison scripts** → Place in `scripts/debug/`

### Script Guidelines

1. ✅ Include docstring explaining purpose
2. ✅ Use `argparse` for CLI arguments
3. ✅ Implement proper error handling
4. ✅ Add usage examples in docstring
5. ✅ Use structured logging
6. ✅ Return proper exit codes (0=success, 1=error, 130=interrupted)

---

## Related Documentation

- [PHASE2_README.md](../PHASE2_README.md) - Phase 2 architecture and components
- [QUICKSTART.md](../QUICKSTART.md) - System quick start guide
- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - Full system architecture
- [docs/API_CONTRACTS.md](../docs/API_CONTRACTS.md) - Component interfaces

---

**Last Updated:** January 29, 2026
