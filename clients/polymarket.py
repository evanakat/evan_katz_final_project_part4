"""Polymarket Gamma + CLOB API client.

Two endpoints are used:
  - GET gamma-api.polymarket.com/markets   — list of active markets w/ 24h stats
  - GET clob.polymarket.com/book?token_id= — full L2 order book

Polymarket binary markets each have two ERC-1155 tokens — a YES and a NO
token — and the orderbook is keyed by token id, not market id. We extract
the YES token id during normalization.
"""
from __future__ import annotations

import json
import httpx
from typing import Any

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"


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
                "include_events": "true",
            }
            resp = await client.get(f"{GAMMA_BASE}/markets", params=params)
            resp.raise_for_status()
            batch = resp.json() or []
            if not batch:
                break
            markets.extend(batch)
            offset += len(batch)
            if len(batch) < page_size:
                break
    return markets


async def fetch_orderbook(token_id: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Fetch the CLOB orderbook for a single Polymarket YES token."""
    if not token_id:
        return None
    try:
        resp = await client.get(f"{CLOB_BASE}/book", params={"token_id": token_id})
        if resp.status_code != 200:
            return None
        payload = resp.json() or {}
    except Exception:
        return None

    bids: list[dict[str, float]] = []
    for b in payload.get("bids") or []:
        try:
            bids.append({"price": float(b["price"]), "size": float(b["size"])})
        except (KeyError, TypeError, ValueError):
            continue

    asks: list[dict[str, float]] = []
    for a in payload.get("asks") or []:
        try:
            asks.append({"price": float(a["price"]), "size": float(a["size"])})
        except (KeyError, TypeError, ValueError):
            continue

    bids.sort(key=lambda x: x["price"], reverse=True)
    asks.sort(key=lambda x: x["price"])
    return {"bids": bids, "asks": asks}


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

    yes_idx = 0
    if outcomes:
        yes_idx = next(
            (i for i, o in enumerate(outcomes) if str(o).strip().lower() == "yes"),
            0,
        )

    yes_price = 0.0
    if prices:
        try:
            yes_price = float(prices[yes_idx])
        except (ValueError, IndexError, TypeError):
            yes_price = _as_float(prices[0]) if prices else 0.0

    if not yes_price:
        yes_price = _as_float(m.get("lastTradePrice"))

    clob_tokens = _maybe_json(m.get("clobTokenIds")) or []
    yes_token_id = ""
    if clob_tokens:
        try:
            yes_token_id = str(clob_tokens[yes_idx])
        except (IndexError, TypeError):
            yes_token_id = str(clob_tokens[0]) if clob_tokens else ""

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
        "book_key": yes_token_id,
    }
