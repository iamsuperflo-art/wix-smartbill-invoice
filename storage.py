"""
Idempotență: ținem evidența comenzilor deja facturate, ca un webhook repetat
să nu emită o a doua factură pentru aceeași comandă.

SQLite e suficient. Pe Railway atașează un Volume (DB_PATH=/data/invoices.db),
altfel evidența se pierde la redeploy.
"""
import os
import sqlite3
import threading

import config

_lock = threading.Lock()


def _conn():
    os.makedirs(os.path.dirname(config.DB_PATH) or ".", exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.execute("""
        CREATE TABLE IF NOT EXISTS invoiced (
            order_id   TEXT PRIMARY KEY,
            series     TEXT,
            number     TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return c


def already_invoiced(order_id: str) -> dict | None:
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT series, number FROM invoiced WHERE order_id = ?",
            (order_id,),
        ).fetchone()
    if row:
        return {"series": row[0], "number": row[1]}
    return None


def mark_invoiced(order_id: str, series: str, number: str) -> None:
    with _lock, _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO invoiced (order_id, series, number) VALUES (?, ?, ?)",
            (order_id, series, number),
        )
        c.commit()
