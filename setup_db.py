import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

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

DB_NAME = "candles"
CONN_PARAMS = {
    "host": "172.17.0.1",
    "port": 5433,
    "user": "postgres",
    "password": "trading123",
}


def create_database():
    conn = psycopg2.connect(**CONN_PARAMS, dbname="postgres")
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME)))
        print(f"Database '{DB_NAME}' created.")
    else:
        print(f"Database '{DB_NAME}' already exists.")
    cur.close()
    conn.close()


def create_tables():
    conn = psycopg2.connect(**CONN_PARAMS, dbname=DB_NAME)
    cur = conn.cursor()
    for table_name in TABLES:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                timestamp BIGINT PRIMARY KEY UNIQUE,
                open DOUBLE PRECISION NOT NULL,
                high DOUBLE PRECISION NOT NULL,
                low DOUBLE PRECISION NOT NULL,
                close DOUBLE PRECISION NOT NULL,
                volume DOUBLE PRECISION NOT NULL
            );
        """)
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp ON {table_name} (timestamp);
        """)
        print(f"Table '{table_name}' ensured.")
    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    create_database()
    create_tables()
    print("Setup complete.")
