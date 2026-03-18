import sqlite3
import time

DB_NAME = "data.db"


def get_connection():
    return sqlite3.connect(
        DB_NAME,
        timeout=10,
        check_same_thread=False,
    )


def _fdv_cell(fdv):
    """DB cell: numeric string or 'late' (never NULL for written snapshots)."""
    if fdv is None:
        return "late"
    return f"{round(float(fdv), 2)}"


def update_trade_5m(trade_id, fdv_usd):
    """fdv_usd None -> store 'late'."""
    for attempt in range(3):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE trades
                SET value_5m = ?, timestamp_5m = datetime('now')
                WHERE id = ?
                """,
                (_fdv_cell(fdv_usd), trade_id),
            )
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                time.sleep(0.5)
            else:
                raise


def update_trade_15m(trade_id, fdv_usd):
    for attempt in range(3):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE trades
                SET value_15m = ?, timestamp_15m = datetime('now')
                WHERE id = ?
                """,
                (_fdv_cell(fdv_usd), trade_id),
            )
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                time.sleep(0.5)
            else:
                raise


def mark_missed_fdv_snapshots():
    """
    Rows past due with no snapshot (e.g. app was down): set 'late' instead of NULL.
    """
    for attempt in range(3):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE trades
                SET value_5m = 'late', timestamp_5m = datetime('now')
                WHERE pool_address IS NOT NULL
                  AND pool_address != ''
                  AND (value_5m IS NULL OR value_5m = '')
                  AND datetime(timestamp, '+5 minutes') < datetime('now')
                """
            )
            cursor.execute(
                """
                UPDATE trades
                SET value_15m = 'late', timestamp_15m = datetime('now')
                WHERE pool_address IS NOT NULL
                  AND pool_address != ''
                  AND (value_15m IS NULL OR value_15m = '')
                  AND datetime(timestamp, '+15 minutes') < datetime('now')
                """
            )
            conn.commit()
            conn.close()
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e):
                time.sleep(0.5)
            else:
                raise


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
    """Creates trades table. For a clean schema, remove data.db first."""
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
            value_5m TEXT,
            timestamp_5m DATETIME,
            value_15m TEXT,
            timestamp_15m DATETIME,
            pool_address TEXT
        )
        """
    )

    conn.commit()
    conn.close()
