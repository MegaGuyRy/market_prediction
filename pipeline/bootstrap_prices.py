import os
import pandas as pd
import yfinance as yf
from tqdm import tqdm

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.dialects.postgresql import insert

DATABASE_URL = os.environ["DATABASE_URL"]
ENGINE = create_engine(DATABASE_URL)

UNIVERSE_PATH = "configs/universe.csv"
START_DATE = "2015-01-01"


def load_universe():
    return pd.read_csv(UNIVERSE_PATH)["symbol"].dropna().unique().tolist()


def fetch_prices(symbol: str) -> pd.DataFrame | None:
    df = yf.download(symbol, start=START_DATE, auto_adjust=True, progress=False)
    if df.empty:
        return None

    df = df.reset_index()
    
    # Fix MultiIndex columns if present (flatten to single level)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # ensure Postgres DATE compatibility
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

    # convert NaN -> None for SQL
    out = out.where(pd.notnull(out), None)

    # convert numpy types to python types (helps some drivers)
    for c in ["open", "high", "low", "close", "adj_close"]:
        out[c] = out[c].astype(object).where(out[c].notna(), None)
    
    # Handle volume conversion properly
    out["volume"] = out["volume"].astype(object).where(out["volume"].notna(), None)

    return out


def upsert_dataframe(df: pd.DataFrame, table_name: str = "price_bars_daily", chunk_size: int = 1000):
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
    symbols = load_universe()

    for symbol in tqdm(symbols, desc="Bootstrapping prices"):
        df = fetch_prices(symbol)
        if df is None:
            print(f"No data for {symbol}")
            continue

        upsert_dataframe(df, "price_bars_daily")


if __name__ == "__main__":
    main()
