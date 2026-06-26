import time
import psycopg2
from psycopg2 import sql
from datetime import datetime, timezone
import ccxt


DB_CONFIG = {
    "host": "172.17.0.1",
    "port": 5433,
    "dbname": "candles",
    "user": "postgres",
    "password": "trading123",
}

SYMBOLS = ["BTC/USDT", "SOL/USDT", "ETH/USDT", "ADA/USDT", "TRX/USDT", "ZEC/USDT"]
TIMEFRAMES = ["5m", "15m", "1h"]
START_MS = 1704067200000  # 2024-01-01 00:00:00 UTC
MAX_RETRIES = 5


def symbol_to_table_suffix(symbol: str) -> str:
    return symbol.replace("/", "").lower()


def table_name(symbol: str, timeframe: str) -> str:
    return f"binance_spot_{symbol_to_table_suffix(symbol)}_{timeframe}"


def get_resume_since(conn, tbl: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT MAX(timestamp) FROM {tbl}").format(tbl=sql.Identifier(tbl)))
        row = cur.fetchone()
    if row and row[0] is not None:
        return row[0] + 1
    return START_MS


def insert_candles(conn, tbl: str, candles: list) -> None:
    if not candles:
        return
    with conn.cursor() as cur:
        cur.executemany(
            sql.SQL(
                """
                INSERT INTO {tbl} (timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp) DO NOTHING
                """
            ).format(tbl=sql.Identifier(tbl)),
            candles,
        )
    conn.commit()


def fetch_with_retry(exchange, symbol, timeframe, since, label):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        except (ccxt.RequestTimeout, ccxt.NetworkError) as e:
            wait = 2 ** attempt
            print(f"{label} Timeout/network error (attempt {attempt}/{MAX_RETRIES}), retrying in {wait}s: {e}")
            time.sleep(wait)
    raise RuntimeError(f"{label} Failed after {MAX_RETRIES} retries")


def download_symbol_timeframe(exchange, symbol, timeframe, conn) -> None:
    tbl = table_name(symbol, timeframe)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    since = get_resume_since(conn, tbl)
    total = 0
    label = f"[{symbol} {timeframe}]"

    if since > START_MS:
        resume_dt = datetime.fromtimestamp((since - 1) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"{label} Resuming from {resume_dt} UTC")
    else:
        print(f"{label} Starting from 2024-01-01")

    while True:
        candles = fetch_with_retry(exchange, symbol, timeframe, since, label)
        if not candles:
            print(f"{label} No more candles returned. Done.")
            break

        insert_candles(conn, tbl, candles)
        total += len(candles)

        last_ts = candles[-1][0]
        last_dt = datetime.fromtimestamp(last_ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        print(f"{label} Fetched {len(candles)} candles up to {last_dt} UTC (total this run: {total})")

        if last_ts >= now_ms:
            print(f"{label} Reached current time. Done.")
            break

        since = last_ts + 1
        time.sleep(0.2)


def print_summary(conn) -> None:
    tables = [table_name(s, tf) for s in SYMBOLS for tf in TIMEFRAMES]

    print("\n" + "=" * 60)
    print(f"{'Table':<45} {'Rows':>10}")
    print("=" * 60)

    with conn.cursor() as cur:
        for tbl in tables:
            try:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {tbl}").format(tbl=sql.Identifier(tbl)))
                count = cur.fetchone()[0]
            except Exception:
                conn.rollback()
                count = "N/A"
            print(f"{tbl:<45} {str(count):>10}")

    print("=" * 60)


def main() -> None:
    exchange = ccxt.binance({"enableRateLimit": True})
    conn = psycopg2.connect(**DB_CONFIG)

    try:
        for symbol in SYMBOLS:
            for timeframe in TIMEFRAMES:
                download_symbol_timeframe(exchange, symbol, timeframe, conn)

        print_summary(conn)
        print("\nAll tables filled with candles.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
