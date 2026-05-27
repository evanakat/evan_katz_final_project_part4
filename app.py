"""Betting Trend Spotter — Flask app entry point."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from flask import Flask, jsonify, render_template, request

from clients import kalshi, polymarket
from trends import classify_signal, compute_standout, explain

app = Flask(__name__)

_CACHE: dict[str, Any] = {"data": None, "ts": 0.0}
CACHE_TTL_SECONDS = 60


async def _fetch_all() -> dict[str, Any]:
    kalshi_task = kalshi.fetch_markets(limit=500)
    poly_task = polymarket.fetch_markets(limit=500)
    k_raw, p_raw = await asyncio.gather(
        kalshi_task, poly_task, return_exceptions=True
    )

    markets: list[dict[str, Any]] = []
    errors: list[str] = []

    if isinstance(k_raw, Exception):
        errors.append(f"Kalshi fetch failed: {k_raw}")
    else:
        for m in k_raw:
            try:
                markets.append(kalshi.normalize(m))
            except Exception as exc:
                errors.append(f"Kalshi normalize: {exc}")

    if isinstance(p_raw, Exception):
        errors.append(f"Polymarket fetch failed: {p_raw}")
    else:
        for m in p_raw:
            try:
                markets.append(polymarket.normalize(m))
            except Exception as exc:
                errors.append(f"Polymarket normalize: {exc}")

    for m in markets:
        m.update(compute_standout(m))
        m["signal"] = classify_signal(m.get("price_change_24h") or 0.0)
        m["explanation"] = explain(m)

    markets.sort(key=lambda x: x["score"], reverse=True)
    return {"markets": markets, "errors": errors}


def _load_cached() -> dict[str, Any]:
    now = time.time()
    if not _CACHE["data"] or now - _CACHE["ts"] > CACHE_TTL_SECONDS:
        _CACHE["data"] = asyncio.run(_fetch_all())
        _CACHE["ts"] = now
    return _CACHE["data"]


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/trends")
def api_trends():
    data = _load_cached()

    platform = request.args.get("platform", "all").lower()
    try:
        min_vol = float(request.args.get("min_vol", 0))
    except ValueError:
        min_vol = 0.0
    try:
        min_move = float(request.args.get("min_move", 0))
    except ValueError:
        min_move = 0.0
    try:
        limit = int(request.args.get("limit", 100))
    except ValueError:
        limit = 100

    markets = data["markets"]
    if platform != "all":
        markets = [m for m in markets if m["platform"].lower() == platform]
    if min_vol:
        markets = [m for m in markets if (m.get("volume_24h") or 0) >= min_vol]
    if min_move:
        markets = [
            m for m in markets if abs(m.get("price_change_24h") or 0) >= min_move
        ]

    return jsonify(
        {
            "markets": markets[:limit],
            "errors": data["errors"],
            "cached_at": _CACHE["ts"],
            "total_unfiltered": len(data["markets"]),
        }
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True)
