"""Kalshi public API client.

Exposes two read endpoints:
  - GET /markets               — list of open markets (cents-denominated prices)
  - GET /markets/{ticker}/orderbook — full L2 depth, split into YES / NO sides

The orderbook converter folds Kalshi's NO side into "asks on YES" so both
platforms expose a common bid/ask book to the feature extractor.
"""
from __future__ import annotations

import httpx
from typing import Any

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"


async def fetch_markets(limit: int = 500) -> list[dict[str, Any]]:
    """Page through open Kalshi markets until we have `limit` of them."""
    markets: list[dict[str, Any]] = []
    cursor: str | None = None
    async with httpx.AsyncClient(timeout=30.0, headers={"Accept": "application/json"}) as client:
        while len(markets) < limit:
            page_size = min(200, limit - len(markets))
            params: dict[str, Any] = {"limit": page_size, "status": "open"}
            if cursor:
                params["cursor"] = cursor
            resp = await client.get(f"{KALSHI_BASE}/markets", params=params)
            resp.raise_for_status()
            payload = resp.json()
            batch = payload.get("markets") or []
            if not batch:
                break
            markets.extend(batch)
            cursor = payload.get("cursor") or None
            if not cursor:
                break
    return markets


async def fetch_orderbook(ticker: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Fetch the orderbook for a single Kalshi market, converted to YES-side bids/asks."""
    try:
        resp = await client.get(f"{KALSHI_BASE}/markets/{ticker}/orderbook")
        if resp.status_code != 200:
            return None
        payload = resp.json() or {}
    except Exception:
        return None
    return _convert_orderbook(payload.get("orderbook") or {})


def _convert_orderbook(book: dict[str, Any]) -> dict[str, Any]:
    """Kalshi exposes two sides: YES bids (buyers of YES) and NO bids (buyers of NO).

    A NO bid at price P cents is economically a YES ask at (100 - P) cents,
    same size. We rebuild a unified YES-side book so both platforms share a
    schema.
    """
    yes_side = book.get("yes") or []
    no_side = book.get("no") or []

    bids: list[dict[str, float]] = []
    for entry in yes_side:
        try:
            price_c, size = entry[0], entry[1]
        except (TypeError, IndexError):
            continue
        bids.append({"price": float(price_c) / 100.0, "size": float(size)})

    asks: list[dict[str, float]] = []
    for entry in no_side:
        try:
            price_c, size = entry[0], entry[1]
        except (TypeError, IndexError):
            continue
        asks.append({"price": (100.0 - float(price_c)) / 100.0, "size": float(size)})

    bids.sort(key=lambda x: x["price"], reverse=True)
    asks.sort(key=lambda x: x["price"])
    return {"bids": bids, "asks": asks}


def _cents_to_dollars(value: Any) -> float:
    try:
        return float(value) / 100.0
    except (TypeError, ValueError):
        return 0.0


def normalize(m: dict[str, Any]) -> dict[str, Any]:
    """Map a raw Kalshi market into the cross-platform schema."""
    last = _cents_to_dollars(m.get("last_price"))
    yes_bid = _cents_to_dollars(m.get("yes_bid"))
    yes_ask = _cents_to_dollars(m.get("yes_ask"))
    prev = _cents_to_dollars(m.get("previous_yes_bid")) or _cents_to_dollars(m.get("previous_price"))
    mid = (yes_bid + yes_ask) / 2 if (yes_bid or yes_ask) else last
    price = last or mid

    price_change_24h = price - prev if prev else 0.0

    ticker = m.get("ticker") or ""
    event_ticker = m.get("event_ticker") or ""
    search_key = event_ticker or ticker
    url = (
        f"https://kalshi.com/markets?search={search_key}"
        if search_key
        else "https://kalshi.com/markets"
    )

    return {
        "platform": "Kalshi",
        "id": ticker,
        "title": m.get("title") or m.get("subtitle") or ticker,
        "url": url,
        "price": round(price, 4),
        "yes_bid": round(yes_bid, 4),
        "yes_ask": round(yes_ask, 4),
        "volume_24h": _cents_to_dollars(m.get("volume_24h")),
        "volume_total": _cents_to_dollars(m.get("volume")),
        "liquidity": _cents_to_dollars(m.get("liquidity")),
        "price_change_24h": round(price_change_24h, 4),
        "price_change_1h": None,
        "close_time": m.get("close_time"),
        # Kalshi's order-book endpoint is keyed by ticker directly.
        "book_key": ticker,
    }
