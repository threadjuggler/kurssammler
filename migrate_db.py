import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# ── Source database (where the candles already are) ──────────────────────────
SOURCE = {
    "host": "172.17.0.1",
    "port": 5433,
    "dbname": "candles",
    "user": "postgres",
    "password": "trading123",
}

# ── Target database (where you want to copy to) ───────────────────────────────
TARGET = {
    "host": "localhost",       # change to your target host
    "port": 5432,              # change to your target port
    "dbname": "candles",
    "user": "postgres",
    "password": "trading123",  # change to your target password
}

TABLES = [
    "binance_spot_btcusdt_5m",
    "binance_spot_btcusdt_15m",
    "binance_spot_btcusdt_1h",
    "binance_spot_solusdt_5m",
    "binance_spot_solusdt_15m",
    "binance_spot_solusdt_1h",
    "binance_spot_ethusdt_5m",
    "binance_spot_ethusdt_15m",
    "binance_spot_ethusdt_1h",
    "binance_spot_adausdt_5m",
    "binance_spot_adausdt_15m",
    "binance_spot_adausdt_1h",
    "binance_spot_trxusdt_5m",
    "binance_spot_trxusdt_15m",
    "binance_spot_trxusdt_1h",
    "binance_spot_zecusdt_5m",
    "binance_spot_zecusdt_15m",
    "binance_spot_zecusdt_1h",
]

BATCH_SIZE = 10_000


def ensure_database(target_params: dict) -> None:
    params = {k: v for k, v in target_params.items() if k != "dbname"}
    conn = psycopg2.connect(**params, dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_params["dbname"],))
    if not cur.fetchone():
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_params["dbname"])))
        print(f"Created database '{target_params['dbname']}'")
    else:
        print(f"Database '{target_params['dbname']}' already exists.")
    cur.close()
    conn.close()


def ensure_table(cur, table_name: str) -> None:
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            timestamp BIGINT PRIMARY KEY UNIQUE,
            open      DOUBLE PRECISION NOT NULL,
            high      DOUBLE PRECISION NOT NULL,
            low       DOUBLE PRECISION NOT NULL,
            close     DOUBLE PRECISION NOT NULL,
            volume    DOUBLE PRECISION NOT NULL
        )
    """)
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name} (timestamp)
    """)


def copy_table(src_conn, dst_conn, table: str) -> int:
    src_cur = src_conn.cursor()
    dst_cur = dst_conn.cursor()

    ensure_table(dst_cur, table)
    dst_conn.commit()

    src_cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
    total_rows = src_cur.fetchone()[0]

    if total_rows == 0:
        print(f"  {table}: empty, skipping.")
        return 0

    src_cur.execute(
        sql.SQL("SELECT timestamp, open, high, low, close, volume FROM {} ORDER BY timestamp")
        .format(sql.Identifier(table))
    )

    copied = 0
    while True:
        rows = src_cur.fetchmany(BATCH_SIZE)
        if not rows:
            break
        dst_cur.executemany(
            f"""
            INSERT INTO {table} (timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp) DO NOTHING
            """,
            rows,
        )
        dst_conn.commit()
        copied += len(rows)
        print(f"  {table}: {copied}/{total_rows} rows copied...", end="\r")

    print(f"  {table}: {copied}/{total_rows} rows copied.    ")
    src_cur.close()
    dst_cur.close()
    return copied


def main() -> None:
    print("Connecting to source database...")
    src_conn = psycopg2.connect(**SOURCE)

    print("Ensuring target database exists...")
    ensure_database(TARGET)

    print("Connecting to target database...")
    dst_conn = psycopg2.connect(**TARGET)

    total_copied = 0
    print(f"\nMigrating {len(TABLES)} tables (batch size: {BATCH_SIZE:,}):\n")

    for table in TABLES:
        total_copied += copy_table(src_conn, dst_conn, table)

    src_conn.close()
    dst_conn.close()

    print(f"\nDone. {total_copied:,} rows copied in total.")


if __name__ == "__main__":
    main()
