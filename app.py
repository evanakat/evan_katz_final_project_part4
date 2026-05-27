"""Betting Trend Predictor — Flask app entry point.

Pipeline per refresh:
  1. Fetch active markets from Kalshi + Polymarket Gamma.
  2. Normalize into a common schema.
  3. For the top-N by 24h volume per platform, fetch the live order book.
  4. Cross-platform fuzzy-pair markets by title.
  5. Extract pre-move features + score each market.
  6. Persist a snapshot row per market (for future ML labeling).
  7. Return ranked markets to the dashboard.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx
from flask import Flask, jsonify, render_template, request

from clients import kalshi, polymarket
import features as feat_mod
import pairing
import predictor
import snapshots

app = Flask(__name__)

_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
CACHE_TTL_SECONDS = 60
ORDERBOOK_TOP_N_PER_PLATFORM = 30


async def _fetch_orderbooks(targets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fetch order books in parallel for the chosen target markets."""
    if not targets:
        return {}
    async with httpx.AsyncClient(timeout=15.0, headers={"Accept": "application/json"}) as client:
        tasks = []
        for m in targets:
            key = m.get("book_key") or m.get("id")
            if m["platform"] == "Kalshi":
                tasks.append(kalshi.fetch_orderbook(key, client))
            elif m["platform"] == "Polymarket":
                tasks.append(polymarket.fetch_orderbook(key, client))
            else:
                tasks.append(asyncio.sleep(0, result=None))
        results = await asyncio.gather(*tasks, return_exceptions=True)
    out: dict[str, dict[str, Any]] = {}
    for m, ob in zip(targets, results):
        if isinstance(ob, Exception) or not ob:
            continue
        out[m["id"]] = ob
    return out


async def _fetch_all() -> dict[str, Any]:
    kalshi_task = kalshi.fetch_markets(limit=300)
    poly_task = polymarket.fetch_markets(limit=300)
    k_raw, p_raw = await asyncio.gather(kalshi_task, poly_task, return_exceptions=True)

    markets: list[dict[str, Any]] = []
    errors: list[str] = []

    if isinstance(k_raw, Exception):
        errors.append(f"Kalshi fetch failed: {k_raw}")
    else:
        for raw in k_raw:
            try:
                markets.append(kalshi.normalize(raw))
            except Exception as exc:
                errors.append(f"Kalshi normalize: {exc}")

    if isinstance(p_raw, Exception):
        errors.append(f"Polymarket fetch failed: {p_raw}")
    else:
        for raw in p_raw:
            try:
                markets.append(polymarket.normalize(raw))
            except Exception as exc:
                errors.append(f"Polymarket normalize: {exc}")

    # Pick top-N by 24h volume per platform for orderbook enrichment.
    by_platform: dict[str, list[dict[str, Any]]] = {"Kalshi": [], "Polymarket": []}
    for m in sorted(markets, key=lambda x: x.get("volume_24h") or 0.0, reverse=True):
        bucket = by_platform.get(m["platform"])
        if bucket is not None and len(bucket) < ORDERBOOK_TOP_N_PER_PLATFORM:
            bucket.append(m)
    targets = by_platform["Kalshi"] + by_platform["Polymarket"]
    try:
        orderbooks = await _fetch_orderbooks(targets)
    except Exception as exc:
        errors.append(f"Orderbook fetch failed: {exc}")
        orderbooks = {}

    pairs = pairing.find_pairs(markets)
    market_by_id = {m["id"]: m for m in markets}
    for mid, (paired_id, sim) in pairs.items():
        if mid in market_by_id and paired_id in market_by_id:
            market_by_id[mid]["_pair_similarity"] = sim

    # Features + predictions.
    for m in markets:
        ob = orderbooks.get(m["id"])
        paired = None
        pair_info = pairs.get(m["id"])
        if pair_info:
            peer = market_by_id.get(pair_info[0])
            if peer is not None:
                peer_view = dict(peer)
                peer_view["_pair_similarity"] = pair_info[1]
                paired = peer_view
        f = feat_mod.compute(m, orderbook=ob, paired=paired)
        m["features"] = f
        m.update(predictor.predict(f))
        m["explanation"] = predictor.explain(m)
        if paired:
            m["paired_title"] = paired.get("title")
            m["paired_url"] = paired.get("url")
            m["paired_platform"] = paired.get("platform")
            m["paired_similarity"] = pair_info[1] if pair_info else None

    # Snapshot for future ML labeling. Best-effort.
    snapshot_rows = snapshots.record_batch(markets)

    markets.sort(key=lambda x: x.get("pre_move_score") or 0.0, reverse=True)
    return {
        "markets": markets,
        "errors": errors,
        "orderbooks_fetched": len(orderbooks),
        "pairs_found": sum(1 for _ in pairs) // 2,
        "snapshot_rows": snapshot_rows,
    }


def _load_cached() -> dict[str, Any]:
    now = time.time()
    if not _CACHE["data"] or now - _CACHE["ts"] > CACHE_TTL_SECONDS:
        _CACHE["data"] = asyncio.run(_fetch_all())
        _CACHE["ts"] = now
    return _CACHE["data"]


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/predictions")
def api_predictions():
    data = _load_cached()

    platform = request.args.get("platform", "all").lower()
    try:
        min_vol = float(request.args.get("min_vol", 0))
    except ValueError:
        min_vol = 0.0
    try:
        min_score = float(request.args.get("min_score", 0))
    except ValueError:
        min_score = 0.0
    direction_filter = request.args.get("direction", "all").lower()
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        limit = 50

    markets = data["markets"]
    if platform != "all":
        markets = [m for m in markets if m["platform"].lower() == platform]
    if min_vol:
        markets = [m for m in markets if (m.get("volume_24h") or 0) >= min_vol]
    if min_score:
        markets = [m for m in markets if (m.get("pre_move_score") or 0) >= min_score]
    if direction_filter == "up":
        markets = [m for m in markets if (m.get("direction") or 0) > 0.1]
    elif direction_filter == "down":
        markets = [m for m in markets if (m.get("direction") or 0) < -0.1]

    return jsonify(
        {
            "markets": markets[:limit],
            "errors": data["errors"],
            "cached_at": _CACHE["ts"],
            "total_unfiltered": len(data["markets"]),
            "orderbooks_fetched": data.get("orderbooks_fetched", 0),
            "pairs_found": data.get("pairs_found", 0),
            "snapshot_rows": data.get("snapshot_rows", 0),
        }
    )


@app.route("/api/snapshots/stats")
def api_snapshot_stats():
    return jsonify(snapshots.stats())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
