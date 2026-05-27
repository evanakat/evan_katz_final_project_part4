"""Polymarket Gamma API client.

The Gamma API at https://gamma-api.polymarket.com/markets returns active
markets along with 24h volume, last trade price, and pre-computed 1h/24h
price deltas, which is exactly what the trend scorer needs.
"""
from __future__ import annotations

import json
import httpx
from typing import Any

POLY_BASE = "https://gamma-api.polymarket.com"


async def fetch_markets(limit: int = 500) -> list[dict[str, Any]]:
    """Fetch active, open Polymarket markets, ordered by 24h volume."""
    markets: list[dict[str, Any]] = []
    offset = 0
    async with httpx.AsyncClient(timeout=30.0, headers={"Accept": "application/json"}) as client:
        while len(markets) < limit:
            page_size = min(100, limit - len(markets))
            params: dict[str, Any] = {
                "active": "true",
                "closed": "false",
                "archived": "false",
                "limit": page_size,
                "offset": offset,
                "order": "volume24hr",
                "ascending": "false",
                # Ensures each market includes its parent event(s) so we can
                # build a working polymarket.com/event/{slug} URL even for
                # multi-outcome contests.
                "include_events": "true",
            }
            resp = await client.get(f"{POLY_BASE}/markets", params=params)
            resp.raise_for_status()
            batch = resp.json() or []
            if not batch:
                break
            markets.extend(batch)
            offset += len(batch)
            if len(batch) < page_size:
                break
    return markets


def _maybe_json(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize(m: dict[str, Any]) -> dict[str, Any]:
    """Map a raw Polymarket market into the cross-platform schema."""
    outcomes = _maybe_json(m.get("outcomes")) or []
    prices = _maybe_json(m.get("outcomePrices")) or []

    yes_price = 0.0
    if outcomes and prices:
        yes_idx = next(
            (i for i, o in enumerate(outcomes) if str(o).strip().lower() == "yes"),
            0,
        )
        try:
            yes_price = float(prices[yes_idx])
        except (ValueError, IndexError, TypeError):
            yes_price = _as_float(prices[0]) if prices else 0.0

    if not yes_price:
        yes_price = _as_float(m.get("lastTradePrice"))

    # Polymarket's canonical URL is /event/{event-slug}. For binary markets the
    # market slug equals the event slug, but for multi-outcome markets each
    # candidate is its own market with a distinct slug and only the parent
    # event slug actually resolves. Prefer the parent event's slug when the
    # API includes it.
    event_slug = ""
    events = m.get("events")
    if isinstance(events, list) and events:
        first = events[0]
        if isinstance(first, dict):
            event_slug = first.get("slug") or ""
    market_slug = m.get("slug") or ""
    slug = event_slug or market_slug
    url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com/"

    return {
        "platform": "Polymarket",
        "id": m.get("conditionId") or m.get("id") or slug,
        "title": m.get("question") or m.get("slug") or "Polymarket market",
        "url": url,
        "price": round(yes_price, 4),
        "yes_bid": round(_as_float(m.get("bestBid"), yes_price), 4),
        "yes_ask": round(_as_float(m.get("bestAsk"), yes_price), 4),
        "volume_24h": _as_float(m.get("volume24hr")),
        "volume_total": _as_float(m.get("volume")),
        "liquidity": _as_float(m.get("liquidity")),
        "price_change_24h": round(_as_float(m.get("oneDayPriceChange")), 4),
        "price_change_1h": round(_as_float(m.get("oneHourPriceChange")), 4),
        "close_time": m.get("endDate"),
    }
