#!/usr/bin/env python3
"""
Integration test script to verify Phase 1 infrastructure.

Tests:
1. Database connectivity
2. Ollama API connectivity
3. Config loading
4. Logging functionality
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_database_url, get_ollama_url, load_all_configs
from src.utils.logging import setup_logging, StructuredLogger

import requests
from sqlalchemy import create_engine, text


def test_database_connection():
    """Test PostgreSQL connection."""
    print("\n=== Testing Database Connection ===")
    try:
        db_url = get_database_url()
        
        # If running from host (not docker), use localhost:5433
        if 'postgres:5432' in db_url:
            db_url = db_url.replace('postgres:5432', 'localhost:5433')
            print("   (Adjusted for host connection)")
        
        print(f"Database URL: {db_url.replace('market:market', 'market:***')}")
        
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"[DONE] Connected to PostgreSQL")
            print(f"   Version: {version[:50]}...")
            
            # Test pgvector
            result = conn.execute(text("SELECT extname, extversion FROM pg_extension WHERE extname='vector'"))
            ext = result.fetchone()
            if ext:
                print(f"[DONE] pgvector extension: {ext[1]}")
            else:
                print(f"⚠️  pgvector extension not found")
            
            # Count tables
            result = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'"
            ))
            table_count = result.scalar()
            print(f"[DONE] Tables in database: {table_count}")
            
            # Count price data
            try:
                result = conn.execute(text("SELECT COUNT(*) FROM ohlcv"))
                row_count = result.scalar()
                print(f"[DONE] Rows in ohlcv table: {row_count:,}")
            except Exception:
                # Table might be empty
                print(f"⚠️  ohlcv table is empty or doesn't exist yet")
            
        return True
    except Exception as e:
        print(f"[Fail] Database connection failed: {e}")
        return False


def test_ollama_connection():
    """Test Ollama API connection."""
    print("\n=== Testing Ollama Connection ===")
    try:
        ollama_url = get_ollama_url()
        
        # If running from host (not docker), use localhost:11434
        if 'ollama:11434' in ollama_url:
            ollama_url = ollama_url.replace('ollama:11434', 'localhost:11434')
            print("   (Adjusted for host connection)")
        
        print(f"Ollama URL: {ollama_url}")
        
        # Test /api/tags endpoint
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        
        models = response.json().get('models', [])
        print(f"[DONE] Connected to Ollama")
        print(f"   Available models: {len(models)}")
        for model in models:
            print(f"   - {model['name']} ({model['details']['parameter_size']})")
        
        # Test inference
        print("\n   Testing inference...")
        inference_response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": "mistral",
                "prompt": "Say 'OK' if you can read this.",
                "stream": False
            },
            timeout=30
        )
        inference_response.raise_for_status()
        
        result = inference_response.json()
        print(f"[DONE] Inference test passed")
        print(f"   Response: {result.get('response', '')[:100]}")
        
        return True
    except Exception as e:
        print(f"[Fail] Ollama connection failed: {e}")
        return False


def test_config_loading():
    """Test configuration loading."""
    print("\n=== Testing Config Loading ===")
    try:
        configs = load_all_configs()
        
        print(f"[DONE] Loaded {len(configs)} config files:")
        for name, config in configs.items():
            print(f"   - {name}.yaml ({len(config)} top-level keys)")
        
        # Check specific config values
        settings = configs['settings']
        print(f"\n   Universe: {settings['universe']['type']} ({settings['universe']['size']} stocks)")
        print(f"   Max positions: {settings['portfolio']['max_positions']}")
        print(f"   Risk per trade: {settings['risk']['risk_per_trade_pct']}%")
        print(f"   Drawdown limits: {settings['risk']['soft_drawdown_limit_pct']}% / {settings['risk']['hard_drawdown_limit_pct']}%")
        
        models = configs['models']
        print(f"\n   ML Model: XGBoost")
        print(f"   Training lookback: {models['xgboost']['training']['lookback_days']} days")
        print(f"   Retrain frequency: {models['xgboost']['training']['retrain_frequency_days']} days")
        
        return True
    except Exception as e:
        print(f"[Fail] Config loading failed: {e}")
        return False


def test_logging():
    """Test logging functionality."""
    print("\n=== Testing Logging ===")
    try:
        # Setup logger
        logger = StructuredLogger(setup_logging({'level': 'INFO', 'format': 'json'}))
        
        print("[DONE] Logger initialized")
        
        # Test different log types
        logger.info("Test info message", test=True)
        logger.log_signal("AAPL", "BUY", 0.85, expected_return=0.02)
        logger.log_trade("MSFT", "BUY", 100, 350.50, order_id="test123")
        logger.log_portfolio_state(100000.0, 50000.0, 5, unrealized_pnl=2500.0)
        
        print("[DONE] Logging test passed (check console output above for JSON logs)")
        
        return True
    except Exception as e:
        print(f"[Fail] Logging test failed: {e}")
        return False


def main():
    """Run all integration tests."""
    print("=" * 60)
    print("PHASE 1 INTEGRATION TESTS")
    print("=" * 60)
    
    results = {
        'Database Connection': test_database_connection(),
        'Ollama Connection': test_ollama_connection(),
        'Config Loading': test_config_loading(),
        'Logging': test_logging()
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "[DONE] PASS" if result else "[Fail] FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All integration tests passed! Phase 1 infrastructure is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
