"""Kalshi public API client.

Kalshi exposes an unauthenticated read endpoint at
https://api.elections.kalshi.com/trade-api/v2/markets. Prices are returned
in cents (0-100); we convert to dollars (0-1) so both platforms share a
schema.
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

    # Kalshi exposes `previous_yes_bid` as "before today's session", which is
    # the closest proxy to a 24h baseline on the markets list endpoint.
    price_change_24h = price - prev if prev else 0.0

    ticker = m.get("ticker") or ""
    event_ticker = m.get("event_ticker") or ""
    url = (
        f"https://kalshi.com/markets/{event_ticker.lower()}/{ticker.lower()}"
        if event_ticker
        else f"https://kalshi.com/markets/{ticker.lower()}"
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
    }
