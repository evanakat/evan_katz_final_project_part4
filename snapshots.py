"""SQLite snapshot logger.

Every time the dashboard refreshes, we append one row per market with the
current feature vector and prediction. Once you've accumulated a few
weeks of snapshots you can join each row against the *future* price for
the same market to label whether a meaningful move actually happened —
then train a real classifier on the same feature columns the heuristic
predictor already uses.

The DB path is overridable via the SNAPSHOT_DB env var; default is
`./snapshots.db`. Set SNAPSHOT_DB=":memory:" to disable persistence
(useful in tests).
"""
from __future__ import annotations

import os
import sqlite3
import time
from typing import Any, Iterable

_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    platform TEXT NOT NULL,
    market_id TEXT NOT NULL,
    title TEXT,
    price REAL,
    yes_bid REAL,
    yes_ask REAL,
    spread REAL,
    spread_pct REAL,
    volume_24h REAL,
    volume_total REAL,
    liquidity REAL,
    vol_share_24h REAL,
    price_change_1h REAL,
    price_change_24h REAL,
    accel REAL,
    book_bid_size REAL,
    book_ask_size REAL,
    book_imbalance REAL,
    book_depth_usd REAL,
    has_book INTEGER,
    arb_gap REAL,
    paired_platform TEXT,
    paired_id TEXT,
    paired_similarity REAL,
    pre_move_score REAL,
    direction REAL,
    direction_label TEXT
);

CREATE INDEX IF NOT EXISTS idx_market_ts
    ON market_snapshots (market_id, ts);

CREATE INDEX IF NOT EXISTS idx_ts
    ON market_snapshots (ts);
"""


def _db_path() -> str:
    return os.environ.get("SNAPSHOT_DB", "snapshots.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.executescript(_SCHEMA)
    return conn


def record_batch(markets: Iterable[dict[str, Any]]) -> int:
    """Append one row per market. Returns rows written. Best-effort: any
    error is swallowed so a logging hiccup never breaks the dashboard."""
    ts = time.time()
    rows: list[tuple] = []
    for m in markets:
        feats = m.get("features") or {}
        rows.append(
            (
                ts,
                m.get("platform"),
                m.get("id"),
                m.get("title"),
                m.get("price"),
                m.get("yes_bid"),
                m.get("yes_ask"),
                feats.get("spread"),
                feats.get("spread_pct"),
                feats.get("volume_24h"),
                m.get("volume_total"),
                m.get("liquidity"),
                feats.get("vol_share_24h"),
                feats.get("price_change_1h"),
                feats.get("price_change_24h"),
                feats.get("accel"),
                feats.get("book_bid_size"),
                feats.get("book_ask_size"),
                feats.get("book_imbalance"),
                feats.get("book_depth_usd"),
                1 if feats.get("has_book") else 0,
                feats.get("arb_gap"),
                feats.get("paired_platform"),
                feats.get("paired_id"),
                feats.get("paired_similarity"),
                m.get("pre_move_score"),
                m.get("direction"),
                m.get("direction_label"),
            )
        )
    if not rows:
        return 0
    try:
        with _connect() as conn:
            conn.executemany(
                """
                INSERT INTO market_snapshots (
                    ts, platform, market_id, title,
                    price, yes_bid, yes_ask, spread, spread_pct,
                    volume_24h, volume_total, liquidity, vol_share_24h,
                    price_change_1h, price_change_24h, accel,
                    book_bid_size, book_ask_size, book_imbalance,
                    book_depth_usd, has_book,
                    arb_gap, paired_platform, paired_id, paired_similarity,
                    pre_move_score, direction, direction_label
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                rows,
            )
            return len(rows)
    except sqlite3.Error:
        return 0


def stats() -> dict[str, Any]:
    """Return basic DB stats for the dashboard footer."""
    try:
        with _connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*), MIN(ts), MAX(ts), COUNT(DISTINCT market_id) "
                "FROM market_snapshots"
            )
            row = cur.fetchone() or (0, None, None, 0)
            count, first_ts, last_ts, n_markets = row
            return {
                "snapshots": int(count or 0),
                "first_ts": first_ts,
                "last_ts": last_ts,
                "markets_tracked": int(n_markets or 0),
                "path": _db_path(),
            }
    except sqlite3.Error as e:
        return {"snapshots": 0, "error": str(e), "path": _db_path()}
