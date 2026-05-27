"""Pre-move feature extraction.

Each feature is a scalar in roughly comparable range so the predictor can
blend them by weight. Features are computed from:
  - the normalized market dict (price, volumes, recent change),
  - the L2 orderbook (when fetched — only top-volume markets get one),
  - the paired cross-platform market (when a fuzzy title match exists).

Every feature is also exported via `to_record()` so it lands cleanly in
the snapshot database for later ML training.
"""
from __future__ import annotations

from typing import Any

BOOK_DEPTH_LEVELS = 5  # how many L2 levels to aggregate for depth/imbalance


def _book_side_size(side: list[dict[str, float]]) -> float:
    return sum(level.get("size", 0.0) for level in side[:BOOK_DEPTH_LEVELS])


def _book_side_value(side: list[dict[str, float]]) -> float:
    return sum(
        level.get("price", 0.0) * level.get("size", 0.0)
        for level in side[:BOOK_DEPTH_LEVELS]
    )


def compute(
    market: dict[str, Any],
    orderbook: dict[str, Any] | None = None,
    paired: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract a feature dict for one market."""
    feats: dict[str, Any] = {}

    # ---- Volume share: recent activity vs lifetime ----
    vol_total = market.get("volume_total") or 0.0
    vol_24h = market.get("volume_24h") or 0.0
    feats["vol_share_24h"] = vol_24h / vol_total if vol_total > 0 else 0.0
    feats["volume_24h"] = vol_24h

    # ---- Spread (tighter = more confident pricing) ----
    bid = market.get("yes_bid") or 0.0
    ask = market.get("yes_ask") or 0.0
    mid = (bid + ask) / 2 if (bid and ask) else (market.get("price") or 0.0)
    spread = max(ask - bid, 0.0) if (bid and ask) else 0.0
    feats["spread"] = spread
    feats["spread_pct"] = (spread / mid) if mid > 0 else 0.0

    # ---- Momentum acceleration: 1h move vs average hourly over 24h ----
    ch_1h = market.get("price_change_1h")
    ch_24h = market.get("price_change_24h") or 0.0
    if ch_1h is None:
        feats["accel"] = 0.0
        feats["recent_direction"] = 0.0
    else:
        avg_hourly = max(abs(ch_24h) / 24.0, 0.001)
        feats["accel"] = abs(ch_1h) / avg_hourly
        feats["recent_direction"] = ch_1h
    feats["price_change_1h"] = ch_1h if ch_1h is not None else 0.0
    feats["price_change_24h"] = ch_24h

    # ---- Order-book imbalance: top-5 bid size vs ask size ----
    book_bid_size = 0.0
    book_ask_size = 0.0
    book_bid_value = 0.0
    book_ask_value = 0.0
    book_imbalance = 0.0
    book_depth_usd = 0.0
    has_book = False
    if orderbook:
        bids = orderbook.get("bids") or []
        asks = orderbook.get("asks") or []
        book_bid_size = _book_side_size(bids)
        book_ask_size = _book_side_size(asks)
        book_bid_value = _book_side_value(bids)
        book_ask_value = _book_side_value(asks)
        total = book_bid_size + book_ask_size
        if total > 0:
            book_imbalance = (book_bid_size - book_ask_size) / total
            has_book = True
        book_depth_usd = book_bid_value + book_ask_value
    feats["book_bid_size"] = book_bid_size
    feats["book_ask_size"] = book_ask_size
    feats["book_imbalance"] = book_imbalance
    feats["book_depth_usd"] = book_depth_usd
    feats["has_book"] = has_book

    # ---- Cross-platform arbitrage gap ----
    arb_gap = 0.0
    paired_price = None
    paired_platform = None
    paired_id = None
    paired_similarity = None
    if paired:
        paired_price = paired.get("price") or 0.0
        # Gap is (this market) - (paired market). Positive gap means our
        # market is higher; if peers are accurate, we expect convergence
        # downward (and vice-versa).
        arb_gap = (market.get("price") or 0.0) - paired_price
        paired_platform = paired.get("platform")
        paired_id = paired.get("id")
        paired_similarity = paired.get("_pair_similarity")
    feats["arb_gap"] = arb_gap
    feats["arb_gap_abs"] = abs(arb_gap)
    feats["paired_price"] = paired_price
    feats["paired_platform"] = paired_platform
    feats["paired_id"] = paired_id
    feats["paired_similarity"] = paired_similarity

    # ---- Price level (room-to-move proxy) ----
    price = market.get("price") or 0.0
    feats["price"] = price
    # max headroom for an upward move is (1-price); downward is price.
    feats["headroom_up"] = max(0.0, 1.0 - price)
    feats["headroom_down"] = max(0.0, price)

    return feats
