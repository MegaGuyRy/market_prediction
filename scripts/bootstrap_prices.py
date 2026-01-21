"""Bootstrap historical price data from Yahoo Finance into PostgreSQL."""

import os
import sys
from pathlib import Path

import pandas as pd
import yfinance as yf
from tqdm import tqdm
from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.dialects.postgresql import insert

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import setup_logging, StructuredLogger
from src.utils.config import get_database_url, load_yaml_config

# Setup logging
config = load_yaml_config('settings')
logger = StructuredLogger(setup_logging(config.get('logging', {})))

DATABASE_URL = get_database_url()
ENGINE = create_engine(DATABASE_URL)

UNIVERSE_PATH = Path(__file__).parent.parent / "configs" / "universe.csv"
START_DATE = "2015-01-01"


def load_universe():
    """Load trading universe from CSV."""
    if not UNIVERSE_PATH.exists():
        logger.warning(f"Universe file not found: {UNIVERSE_PATH}, using default symbols")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "XOM", "UNH"]
    
    df = pd.read_csv(UNIVERSE_PATH)
    symbols = df["symbol"].dropna().unique().tolist()
    logger.info(f"Loaded {len(symbols)} symbols from universe file")
    return symbols


def fetch_prices(symbol: str) -> pd.DataFrame | None:
    """
    Fetch historical prices for a symbol from Yahoo Finance.
    
    Args:
        symbol: Stock ticker symbol
    
    Returns:
        DataFrame with OHLCV data, or None if no data available
    """
    try:
        df = yf.download(symbol, start=START_DATE, auto_adjust=True, progress=False)
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return None

        df = df.reset_index()
        
        # Fix MultiIndex columns if present (flatten to single level)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Ensure Postgres DATE compatibility
        df["Date"] = pd.to_datetime(df["Date"]).dt.date

        df["symbol"] = symbol
        df = df.rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )

        df["adj_close"] = df["close"]

        out = df[["symbol", "date", "open", "high", "low", "close", "adj_close", "volume"]].copy()

        # Convert NaN -> None for SQL
        out = out.where(pd.notnull(out), None)

        # Convert numpy types to python types (helps some drivers)
        for c in ["open", "high", "low", "close", "adj_close"]:
            out[c] = out[c].astype(object).where(out[c].notna(), None)
        
        # Handle volume conversion properly
        out["volume"] = out["volume"].astype(object).where(out["volume"].notna(), None)

        logger.debug(f"Fetched {len(out)} rows for {symbol}")
        return out
        
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}", symbol=symbol, error=str(e))
        return None


def upsert_dataframe(df: pd.DataFrame, table_name: str = "price_bars_daily", chunk_size: int = 1000):
    """
    Upsert DataFrame into PostgreSQL table.
    
    Args:
        df: DataFrame with price data
        table_name: Target table name
        chunk_size: Number of rows per batch
    """
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=ENGINE)

    # Convert to records, ensuring clean data
    records = df.to_dict(orient="records")
    
    # Clean up any empty strings, NaN values, or invalid data
    cleaned_records = []
    for record in records:
        cleaned_record = {}
        for key, value in record.items():
            # Convert empty strings to None
            if value == '':
                cleaned_record[key] = None
            # Handle NaN/NaT values
            elif pd.isna(value):
                cleaned_record[key] = None
            else:
                cleaned_record[key] = value
        cleaned_records.append(cleaned_record)

    with ENGINE.begin() as conn:
        for i in range(0, len(cleaned_records), chunk_size):
            batch = cleaned_records[i : i + chunk_size]
            stmt = insert(table).values(batch)

            update_cols = {
                c.name: getattr(stmt.excluded, c.name)
                for c in table.columns
                if c.name not in ("symbol", "date")
            }

            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "date"],
                set_=update_cols,
            )
            conn.execute(stmt)


def main():
    """Main bootstrap function."""
    logger.log_pipeline_start("bootstrap_prices")
    
    symbols = load_universe()
    logger.info(f"Starting price bootstrap for {len(symbols)} symbols")

    success_count = 0
    fail_count = 0

    for symbol in tqdm(symbols, desc="Bootstrapping prices"):
        df = fetch_prices(symbol)
        if df is None:
            logger.warning(f"No data for {symbol}", symbol=symbol)
            fail_count += 1
            continue

        try:
            upsert_dataframe(df, "price_bars_daily")
            success_count += 1
            logger.info(f"Upserted {len(df)} rows for {symbol}", 
                       symbol=symbol, row_count=len(df))
        except Exception as e:
            logger.error(f"Failed to upsert {symbol}: {e}", 
                        symbol=symbol, error=str(e))
            fail_count += 1

    logger.log_pipeline_complete(
        "bootstrap_prices",
        duration_seconds=0,  # Could add timing if needed
        success_count=success_count,
        fail_count=fail_count,
        total_symbols=len(symbols)
    )
    logger.info(f"Bootstrap complete: {success_count} succeeded, {fail_count} failed")


if __name__ == "__main__":
    main()
