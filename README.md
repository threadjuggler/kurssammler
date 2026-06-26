# Kurssammler — Binance Candle Downloader

Downloads OHLCV candlestick data from Binance and stores it in a PostgreSQL database. Supports resumable downloads, automatic retries, and multiple symbols and timeframes.

---

## Requirements

- Python 3.10+
- PostgreSQL (running and accessible)
- Python packages: `ccxt`, `psycopg2-binary`

Install dependencies:

```bash
pip install ccxt psycopg2-binary
```

---

## Configuration

Both scripts share the same database connection settings. Edit the `DB_CONFIG` / `CONN_PARAMS` block at the top of each file:

```python
DB_CONFIG = {
    "host": "172.17.0.1",   # your PostgreSQL host
    "port": 5433,            # your PostgreSQL port
    "dbname": "candles",
    "user": "postgres",
    "password": "trading123",
}
```

Symbols and timeframes to download are defined in `download_candles.py`:

```python
SYMBOLS = ["BTC/USDT", "SOL/USDT", "ETH/USDT", "ADA/USDT", "TRX/USDT", "ZEC/USDT"]
TIMEFRAMES = ["5m", "15m", "1h"]
START_MS = 1704067200000  # 2024-01-01 00:00:00 UTC
```

Adjust these lists to add or remove trading pairs and intervals. `START_MS` sets the earliest timestamp to fetch (Unix milliseconds).

---

## Usage

### Step 1 — Set up the database

Run this once to create the `candles` database and all tables:

```bash
python setup_db.py
```

This creates 18 tables (one per symbol/timeframe combination), e.g. `binance_spot_btcusdt_5m`, `binance_spot_ethusdt_1h`, etc.

### Step 2 — Download candles

```bash
python download_candles.py
```

The script fetches up to 1000 candles per API call and inserts them in batches. Progress is printed to stdout:

```
[BTC/USDT 5m] Starting from 2024-01-01
[BTC/USDT 5m] Fetched 1000 candles up to 2024-01-04 09:20 UTC (total this run: 1000)
...
[BTC/USDT 5m] Reached current time. Done.
```

At the end a summary table shows the row count for each table.

### Resuming

If the download is interrupted, just run `download_candles.py` again. It reads the latest timestamp from each table and continues from where it left off — no duplicates, no gaps.

---

## Database Schema

Each table has the same structure:

| Column    | Type             | Description                        |
|-----------|------------------|------------------------------------|
| timestamp | BIGINT (PK)      | Unix timestamp in milliseconds     |
| open      | DOUBLE PRECISION | Opening price                      |
| high      | DOUBLE PRECISION | Highest price in the interval      |
| low       | DOUBLE PRECISION | Lowest price in the interval       |
| close     | DOUBLE PRECISION | Closing price                      |
| volume    | DOUBLE PRECISION | Trading volume in base currency    |

An index on `timestamp` is created automatically for fast range queries.

---

## Error Handling

Network errors and timeouts are retried up to 5 times with exponential backoff (2, 4, 8, 16, 32 seconds). If all retries fail, the script exits with an error message.

---

## Adding More Symbols

1. Add the symbol to `SYMBOLS` in `download_candles.py`, e.g. `"XRP/USDT"`.
2. Add the corresponding table names to `TABLES` in `setup_db.py`, e.g.:
   ```
   "binance_spot_xrpusdt_5m",
   "binance_spot_xrpusdt_15m",
   "binance_spot_xrpusdt_1h",
   ```
3. Re-run `setup_db.py` (existing tables are not touched).
4. Run `download_candles.py`.
