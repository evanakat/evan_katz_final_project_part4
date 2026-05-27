"""Heuristic pre-move predictor.

Blends the features from `features.py` into:
  - `pre_move_score` in [0, 1]: how likely a meaningful move is imminent,
  - `direction` in [-1, 1]: bias toward up (+) or down (-),
  - per-signal contributions so the UI can show *why* a market scored high.

This is a transparent rule-based model. The weights below are starting
points calibrated from common prediction-market microstructure wisdom
(order flow > order book > arb spreads > momentum > volume share). Once
the snapshot logger has accumulated labeled history, the same feature
vector can be fed to a trained classifier — see ml/README.md.
"""
from __future__ import annotations

from typing import Any

WEIGHTS = {
    "vol_acceleration": 0.15,
    "book_imbalance": 0.30,
    "momentum_acceleration": 0.25,
    "arb_divergence": 0.30,
}


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _sign(x: float) -> float:
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return 0.0


def predict(feats: dict[str, Any]) -> dict[str, Any]:
    """Return prediction fields for a feature dict.

    Output keys:
      pre_move_score:     0..1
      direction:          -1..+1   (negative = down, positive = up)
      direction_label:    human-readable
      signal_contribs:    {signal_name: contribution_to_score}
      paired_with:        platform of cross-market peer (or None)
    """
    # ---- Magnitude signals (each clipped to 0..1) ----
    vol_share = feats.get("vol_share_24h", 0.0) or 0.0
    # vol_share of 0.5+ means at least half the market's lifetime volume is
    # in the last 24h — very unusual. Saturate at 0.5.
    vol_acc = _clip01(vol_share / 0.5)

    imb_abs = abs(feats.get("book_imbalance", 0.0) or 0.0)
    # imbalance ranges -1..+1; treat 0.5+ as a strong signal.
    book_imb = _clip01(imb_abs / 0.5)

    accel = feats.get("accel", 0.0) or 0.0
    # accel of 5x avg-hourly is "very accelerating"; saturate there.
    mom_acc = _clip01(accel / 5.0)

    arb_abs = feats.get("arb_gap_abs", 0.0) or 0.0
    # a 10-point cross-platform gap is huge; saturate at 0.15.
    arb_div = _clip01(arb_abs / 0.15)

    contribs = {
        "vol_acceleration": round(WEIGHTS["vol_acceleration"] * vol_acc, 4),
        "book_imbalance": round(WEIGHTS["book_imbalance"] * book_imb, 4),
        "momentum_acceleration": round(WEIGHTS["momentum_acceleration"] * mom_acc, 4),
        "arb_divergence": round(WEIGHTS["arb_divergence"] * arb_div, 4),
    }
    score = sum(contribs.values())

    # ---- Direction (combine signed signals) ----
    direction = 0.0
    # Order-book lean: positive imbalance = buyers stacked → up.
    direction += 0.5 * (feats.get("book_imbalance", 0.0) or 0.0)
    # Cross-platform gap: if our price is BELOW the peer, we expect to rise → +direction.
    # arb_gap = (this_price - peer_price); so direction picks up -sign * magnitude.
    arb_gap = feats.get("arb_gap", 0.0) or 0.0
    direction += -_sign(arb_gap) * _clip01(abs(arb_gap) / 0.10) * 0.4
    # Recent momentum
    recent = feats.get("recent_direction", 0.0) or 0.0
    direction += _sign(recent) * _clip01(abs(recent) / 0.05) * 0.2
    # Penalize moves toward an exhausted edge (already near 0 or 1).
    price = feats.get("price", 0.5) or 0.5
    if direction > 0:
        direction *= _clip01((1.0 - price) / 0.5)
    elif direction < 0:
        direction *= _clip01(price / 0.5)

    direction = max(-1.0, min(1.0, direction))

    return {
        "pre_move_score": round(score, 4),
        "direction": round(direction, 4),
        "direction_label": label_direction(direction),
        "signal_contribs": contribs,
        "signals": {
            "vol_acceleration": round(vol_acc, 4),
            "book_imbalance": round(book_imb, 4),
            "momentum_acceleration": round(mom_acc, 4),
            "arb_divergence": round(arb_div, 4),
        },
    }


def label_direction(d: float) -> str:
    if d >= 0.35:
        return "Likely UP"
    if d >= 0.10:
        return "Lean UP"
    if d <= -0.35:
        return "Likely DOWN"
    if d <= -0.10:
        return "Lean DOWN"
    return "No bias"


def explain(market: dict[str, Any]) -> str:
    """One-line, human-readable explanation of the top contributing signal."""
    contribs = market.get("signal_contribs") or {}
    if not contribs:
        return "Not enough data to score."
    top_signal, top_value = max(contribs.items(), key=lambda kv: kv[1])
    feats = market.get("features") or {}
    if top_value < 0.02:
        return "No strong pre-move signal; ranked low."

    if top_signal == "book_imbalance":
        imb = feats.get("book_imbalance", 0.0)
        side = "buy" if imb > 0 else "sell"
        return f"Order book lopsided to the {side} side ({imb:+.2f})."
    if top_signal == "arb_divergence":
        gap = feats.get("arb_gap", 0.0)
        peer = feats.get("paired_platform") or "peer"
        verb = "richer" if gap > 0 else "cheaper"
        return f"Priced {abs(gap)*100:.1f}c {verb} than {peer}; expect convergence."
    if top_signal == "momentum_acceleration":
        accel = feats.get("accel", 0.0)
        return f"Last hour moving {accel:.1f}× the trailing average rate."
    if top_signal == "vol_acceleration":
        share = feats.get("vol_share_24h", 0.0) * 100
        return f"{share:.0f}% of lifetime volume traded in the last 24h."
    return "Multiple weak signals; see breakdown."
