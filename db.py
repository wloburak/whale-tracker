import sqlite3
import time

DB_NAME = "data.db"


def get_connection():
    return sqlite3.connect(
        DB_NAME,
        timeout=10,
        check_same_thread=False,
    )


def insert_trade(token, sol, mc, entry_value=None, pool_address=None):
    for attempt in range(3):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO trades (token, sol, mc, entry_value, pool_address)
                VALUES (?, ?, ?, ?, ?)
                """,
                (token, sol, mc, entry_value, pool_address),
            )

            trade_id = cursor.lastrowid

            conn.commit()
            conn.close()
            return trade_id

        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                time.sleep(0.5)
            else:
                raise

    print("Failed to insert after retries")


def update_entry_value(trade_id, value):
    """Set entry_value (e.g. FDV at alert time). 5m/15m columns unused for now."""
    for attempt in range(3):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE trades SET entry_value = ? WHERE id = ?",
                (value, trade_id),
            )
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                time.sleep(0.5)
            else:
                raise


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            sol REAL,
            mc REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            entry_value REAL,
            value_5m REAL,
            timestamp_5m DATETIME,
            value_15m REAL,
            timestamp_15m DATETIME,
            pool_address TEXT
        )
        """
    )

    conn.commit()
    conn.close()
