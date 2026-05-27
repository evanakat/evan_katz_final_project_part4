"""Cross-platform market pairing by fuzzy title matching.

When the same real-world event ("Will the Fed cut rates in June?") trades
on both Kalshi and Polymarket, a price gap between the two is one of the
strongest pre-move signals available — the laggard tends to converge to
the leader. This module finds those pairs from titles alone, using stdlib
difflib so the app has no extra dependency.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

_BOILERPLATE = re.compile(r"\b(will|the|a|an|be|by|in|on|at|to|of|for|is|are|this|that)\b")
_NON_ALPHANUM = re.compile(r"[^a-z0-9 ]+")
_WHITESPACE = re.compile(r"\s+")


def normalize_title(title: str) -> str:
    """Strip filler words & punctuation so similar questions compare cleanly."""
    if not title:
        return ""
    t = title.lower()
    t = _NON_ALPHANUM.sub(" ", t)
    t = _BOILERPLATE.sub(" ", t)
    t = _WHITESPACE.sub(" ", t).strip()
    return t


def find_pairs(
    markets: list[dict[str, Any]], min_similarity: float = 0.6
) -> dict[str, tuple[str, float]]:
    """Match Kalshi <-> Polymarket markets by normalized title similarity.

    Returns a symmetric mapping: { market_id -> (paired_market_id, similarity) }.
    For each Kalshi market we pick the best Polymarket match (and vice versa)
    above the similarity threshold.
    """
    kalshi = [m for m in markets if m.get("platform") == "Kalshi"]
    poly = [m for m in markets if m.get("platform") == "Polymarket"]
    if not kalshi or not poly:
        return {}

    k_norm = {m["id"]: normalize_title(m.get("title", "")) for m in kalshi}
    p_norm = {m["id"]: normalize_title(m.get("title", "")) for m in poly}

    pairs: dict[str, tuple[str, float]] = {}

    for k in kalshi:
        kt = k_norm[k["id"]]
        if not kt or len(kt) < 5:
            continue
        best_id: str | None = None
        best_score = min_similarity
        for p in poly:
            pt = p_norm[p["id"]]
            if not pt or len(pt) < 5:
                continue
            score = SequenceMatcher(None, kt, pt).ratio()
            if score > best_score:
                best_score = score
                best_id = p["id"]
        if best_id:
            pairs[k["id"]] = (best_id, round(best_score, 3))
            # Only fill the reverse mapping if it improves on the poly side's
            # current best — prevents one strong Kalshi match from blocking a
            # better Poly→Kalshi pairing.
            existing = pairs.get(best_id)
            if not existing or best_score > existing[1]:
                pairs[best_id] = (k["id"], round(best_score, 3))

    return pairs
