"""Trend-detection scoring.

A "standout" market is one where:
  1. Price moved meaningfully over the last 24h (the core signal),
  2. Real money is backing the move (volume), and
  3. Recent direction is consistent (1h move agrees with 24h move).

The score combines those into a single comparable number so the dashboard
can rank cross-platform markets together.
"""
from __future__ import annotations

import math
from typing import Any


def compute_standout(m: dict[str, Any]) -> dict[str, Any]:
    """Return scoring fields for a normalized market dict."""
    price_change_24h = m.get("price_change_24h") or 0.0
    price_change_1h = m.get("price_change_1h")
    volume_24h = max(m.get("volume_24h") or 0.0, 0.0)

    move = abs(price_change_24h)

    # log10 keeps the score from blowing up on whale-volume markets while
    # still rewarding markets that have actual money behind them.
    vol_factor = math.log10(volume_24h + 10.0)

    # Momentum: if the 1h move points the same way as the 24h move, the
    # trend is still active. If they disagree, it's mean-reverting.
    momentum = 1.0
    if price_change_1h is not None and price_change_24h:
        same_sign = (price_change_1h >= 0) == (price_change_24h >= 0)
        if abs(price_change_1h) >= 0.005:
            momentum = 1.4 if same_sign else 0.7

    score = move * vol_factor * momentum

    return {
        "score": round(score, 4),
        "move_factor": round(move, 4),
        "vol_factor": round(vol_factor, 4),
        "momentum_factor": round(momentum, 4),
    }


def classify_signal(price_change_24h: float) -> str:
    """Human-readable label for the size + direction of the 24h move."""
    change = price_change_24h or 0.0
    if abs(change) < 0.02:
        return "Quiet"
    direction = "up" if change > 0 else "down"
    if abs(change) >= 0.15:
        return f"Major move {direction}"
    if abs(change) >= 0.05:
        return f"Moving {direction}"
    return f"Slight {direction}"


def explain(m: dict[str, Any]) -> str:
    """One-line, human-readable rationale for why a market is standing out."""
    move_pct = abs(m.get("price_change_24h") or 0.0) * 100
    direction = "↑" if (m.get("price_change_24h") or 0.0) >= 0 else "↓"
    vol = m.get("volume_24h") or 0.0
    parts = [f"{direction} {move_pct:.1f}% in 24h"]
    if vol >= 1_000_000:
        parts.append(f"on ${vol/1_000_000:.1f}M volume")
    elif vol >= 1_000:
        parts.append(f"on ${vol/1_000:.1f}K volume")
    else:
        parts.append(f"on ${vol:.0f} volume")
    momentum = m.get("momentum_factor")
    if momentum and momentum > 1.0:
        parts.append("trend still building")
    elif momentum and momentum < 1.0:
        parts.append("reversing in the last hour")
    return " — ".join(parts)
