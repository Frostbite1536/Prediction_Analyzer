# prediction_mcp/persistence.py
"""
Optional SQLite persistence for MCP session state.

Allows trades and session metadata to survive server restarts.
Disabled by default — enable with --persist flag or PREDICTION_MCP_DB env var.

Usage:
    store = SessionStore("/path/to/session.db")
    store.save(session)       # persist current state
    store.restore(session)    # reload from disk
    store.close()
"""
import json
import logging
import sqlite3
from datetime import datetime
from typing import Optional

from prediction_analyzer.trade_loader import Trade

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS session_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    market TEXT NOT NULL,
    market_slug TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    price REAL NOT NULL,
    shares REAL NOT NULL,
    cost REAL NOT NULL,
    type TEXT NOT NULL,
    side TEXT NOT NULL,
    pnl REAL NOT NULL DEFAULT 0.0,
    tx_hash TEXT
);
CREATE INDEX IF NOT EXISTS idx_trades_market_slug ON trades(market_slug);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
"""


class SessionStore:
    """SQLite-backed persistence for session state."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        logger.info("Session store opened: %s", db_path)

    def save(self, session) -> None:
        """Persist session trades and metadata to SQLite."""
        cur = self._conn.cursor()
        cur.execute("DELETE FROM trades")
        cur.execute("DELETE FROM session_meta")

        for trade in session.trades:
            ts = trade.timestamp.isoformat() if hasattr(trade.timestamp, "isoformat") else str(trade.timestamp)
            cur.execute(
                "INSERT INTO trades (market, market_slug, timestamp, price, shares, cost, type, side, pnl, tx_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (trade.market, trade.market_slug, ts, trade.price, trade.shares,
                 trade.cost, trade.type, trade.side, trade.pnl, trade.tx_hash),
            )

        if session.source:
            cur.execute("INSERT INTO session_meta (key, value) VALUES (?, ?)", ("source", session.source))

        if session.active_filters:
            cur.execute(
                "INSERT INTO session_meta (key, value) VALUES (?, ?)",
                ("active_filters", json.dumps(session.active_filters)),
            )

        self._conn.commit()
        logger.info("Session saved: %d trades", len(session.trades))

    def restore(self, session) -> bool:
        """Restore session state from SQLite. Returns True if trades were restored."""
        cur = self._conn.cursor()
        rows = cur.execute("SELECT * FROM trades ORDER BY id").fetchall()

        if not rows:
            return False

        trades = []
        for row in rows:
            trades.append(Trade(
                market=row["market"],
                market_slug=row["market_slug"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                price=row["price"],
                shares=row["shares"],
                cost=row["cost"],
                type=row["type"],
                side=row["side"],
                pnl=row["pnl"],
                tx_hash=row["tx_hash"],
            ))

        session.trades = trades
        session.filtered_trades = list(trades)

        # Restore metadata
        meta = {r["key"]: r["value"] for r in cur.execute("SELECT key, value FROM session_meta").fetchall()}
        session.source = meta.get("source")

        filters_json = meta.get("active_filters")
        if filters_json:
            session.active_filters = json.loads(filters_json)
        else:
            session.active_filters = {}

        logger.info("Session restored: %d trades from %s", len(trades), session.source)
        return True

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
