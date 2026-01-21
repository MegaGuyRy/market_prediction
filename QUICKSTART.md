# Quick Start Guide - Phase 1 Complete

## Starting the System

### From the project root:

```bash
cd /home/mip/Desktop/market_prediction/market_prediction

# Start all services in the background
sudo docker compose up -d

# Wait 30 seconds for all services to initialize
sleep 30

# Verify all services are healthy
sudo docker compose ps
```

**Expected output:**
```
NAME              IMAGE                    STATUS              PORTS
market_app        market_prediction-app    Up 30 seconds       (no port exposed)
market_ollama     ollama/ollama:latest     Up 30 seconds       0.0.0.0:11434->11434/tcp
market_postgres   pgvector/pgvector:pg16   Up 30 seconds       0.0.0.0:5433->5432/tcp
```

---

## Running Tests

```bash
# Run all integration tests (from host)
.venv/bin/python scripts/test_integration.py

# View logs
sudo docker compose logs -f postgres
sudo docker compose logs -f ollama
sudo docker compose logs -f app
```

---

## Using Ollama (Mistral 7B)

### From the host:
```bash
# Test inference
curl -X POST http://localhost:11434/api/generate \
  -d '{"model":"mistral","prompt":"Say hello","stream":false}'

# List available models
curl http://localhost:11434/api/tags
```

### From inside app container:
```bash
sudo docker compose exec app bash

# Then inside the container:
curl -X POST http://ollama:11434/api/generate \
  -d '{"model":"mistral","prompt":"Your prompt here","stream":false}'
```

---

## Accessing PostgreSQL

### From the host:
```bash
# Connect via psql
psql -h localhost -p 5433 -U market -d marketdb

# Or via Python
python -c "
import psycopg2
conn = psycopg2.connect('dbname=marketdb user=market password=market host=localhost port=5433')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM ohlcv')
print(cur.fetchone())
"
```

### Database credentials:
- Host: `localhost:5433` (from host), `postgres:5432` (from containers)
- Database: `marketdb`
- User: `market`
- Password: `market`

---

## Configuration

All settings are in YAML:

```bash
cat config/settings.yaml       # System settings, schedule, constraints
cat config/models.yaml         # ML model config
cat config/agents.yaml         # Agent definitions
cat config/risk_rules.yaml     # Risk rules, position sizing
```

---

## Logging

Logs are written to:
- **Console:** Real-time JSON logs
- **File:** `logs/market_trader.log` (with rotation)

View logs from the host:
```bash
# Last 50 lines
tail -50 logs/market_trader.log

# Watch live updates
tail -f logs/market_trader.log
```

---

## Stopping the System

```bash
# Stop all services gracefully
sudo docker compose down

# Remove volumes (careful! deletes data)
sudo docker compose down -v

# View running containers
sudo docker compose ps
```

---

## Troubleshooting

### Services won't stop (permission denied):
```bash
# Force stop
sudo docker compose kill

# Or restart Docker daemon
sudo systemctl restart docker
```

### Ollama not responding:
```bash
# Check Ollama logs
sudo docker compose logs ollama

# Verify model is loaded
curl http://localhost:11434/api/tags

# Restart Ollama
sudo docker compose restart ollama
```

### Database connection failed:
```bash
# Check PostgreSQL is running
sudo docker compose exec postgres psql -U market -d marketdb -c "SELECT 1"

# View schema
sudo docker compose exec postgres psql -U market -d marketdb -c "\dt"
```

### Need a fresh start:
```bash
# Remove all containers and data
sudo docker compose down -v

# Rebuild images
sudo docker compose build

# Start fresh
sudo docker compose up -d
```

---

## Phase 1 Status

✅ All infrastructure complete and tested:
- Docker + services: ✅
- PostgreSQL + schema: ✅
- Ollama + Mistral: ✅
- Config system: ✅
- Logging framework: ✅
- Integration tests: ✅

**Ready for Phase 2: Data Layer implementation**

See `PHASE1_COMPLETE.md` for full details.

---

## Documentation

- **QUICK_REFERENCE.md** - 1-minute overview
- **PROJECT_STATUS.md** - Current status & timeline
- **PHASE1_PROGRESS.md** - Phase 1 detailed progress
- **PHASE1_COMPLETE.md** - Phase 1 completion summary
- **docs/ARCHITECTURE.md** - System design
- **docs/IMPLEMENTATION_ROADMAP.md** - All 8 phases

---

**Last Updated:** January 21, 2026  
**Status:** Phase 1 Complete ✅
