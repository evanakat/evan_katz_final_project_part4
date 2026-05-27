"""Offline tests for features, pairing, predictor, snapshot logger, and
both API normalizers/orderbook converters.

Run: python -m unittest discover -s tests
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest

# Ensure snapshot writes don't touch the real db during tests.
os.environ["SNAPSHOT_DB"] = ":memory:"

from clients import kalshi, polymarket  # noqa: E402
import features as feat_mod  # noqa: E402
import pairing  # noqa: E402
import predictor  # noqa: E402
import snapshots  # noqa: E402


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------


class FeatureTests(unittest.TestCase):
    def test_volume_share_when_24h_dominates(self):
        m = {"volume_24h": 80_000.0, "volume_total": 100_000.0}
        f = feat_mod.compute(m)
        self.assertAlmostEqual(f["vol_share_24h"], 0.8)

    def test_volume_share_zero_when_no_volume(self):
        f = feat_mod.compute({"volume_24h": 0, "volume_total": 0})
        self.assertEqual(f["vol_share_24h"], 0.0)

    def test_book_imbalance_positive_when_bids_outweigh_asks(self):
        book = {
            "bids": [{"price": 0.5, "size": 100}, {"price": 0.49, "size": 200}],
            "asks": [{"price": 0.52, "size": 50}],
        }
        f = feat_mod.compute({"price": 0.5}, orderbook=book)
        self.assertGreater(f["book_imbalance"], 0)
        self.assertTrue(f["has_book"])

    def test_book_imbalance_zero_without_book(self):
        f = feat_mod.compute({"price": 0.5})
        self.assertEqual(f["book_imbalance"], 0.0)
        self.assertFalse(f["has_book"])

    def test_acceleration_when_recent_outpaces_average(self):
        m = {"price_change_1h": 0.03, "price_change_24h": 0.04}
        f = feat_mod.compute(m)
        # avg_hourly = 0.04 / 24 ~= 0.00167, accel = 0.03 / 0.00167 ~= 18
        self.assertGreater(f["accel"], 10)

    def test_arb_gap_uses_paired_market(self):
        m = {"price": 0.45}
        paired = {"price": 0.55, "platform": "Polymarket", "id": "x"}
        f = feat_mod.compute(m, paired=paired)
        self.assertAlmostEqual(f["arb_gap"], -0.10)
        self.assertEqual(f["paired_platform"], "Polymarket")


# ---------------------------------------------------------------------------
# Predictor
# ---------------------------------------------------------------------------


class PredictorTests(unittest.TestCase):
    def test_no_signals_low_score(self):
        f = feat_mod.compute({"price": 0.5, "volume_24h": 0, "volume_total": 1})
        out = predictor.predict(f)
        self.assertLess(out["pre_move_score"], 0.05)
        self.assertEqual(out["direction_label"], "No bias")

    def test_strong_book_imbalance_drives_score_and_direction(self):
        book = {
            "bids": [{"price": 0.5, "size": 1000}],
            "asks": [{"price": 0.52, "size": 50}],
        }
        f = feat_mod.compute({"price": 0.5}, orderbook=book)
        out = predictor.predict(f)
        self.assertGreater(out["pre_move_score"], 0.1)
        self.assertGreater(out["direction"], 0)
        self.assertTrue(out["direction_label"].lower().endswith("up"))

    def test_cross_platform_undervalued_predicts_up(self):
        # this market priced at 0.40, peer at 0.55 → expect UP
        m = {"price": 0.40}
        paired = {"price": 0.55, "platform": "Polymarket", "id": "x"}
        f = feat_mod.compute(m, paired=paired)
        out = predictor.predict(f)
        self.assertGreater(out["direction"], 0)
        self.assertGreater(out["pre_move_score"], 0.05)

    def test_cross_platform_overvalued_predicts_down(self):
        m = {"price": 0.70}
        paired = {"price": 0.50, "platform": "Kalshi", "id": "x"}
        f = feat_mod.compute(m, paired=paired)
        out = predictor.predict(f)
        self.assertLess(out["direction"], 0)

    def test_direction_dampened_near_price_extreme(self):
        # An up-signal at price 0.97 should be heavily discounted.
        book = {
            "bids": [{"price": 0.97, "size": 1000}],
            "asks": [{"price": 0.98, "size": 100}],
        }
        f_extreme = feat_mod.compute({"price": 0.97}, orderbook=book)
        out_extreme = predictor.predict(f_extreme)

        f_mid = feat_mod.compute({"price": 0.50}, orderbook=book)
        out_mid = predictor.predict(f_mid)

        self.assertLess(out_extreme["direction"], out_mid["direction"])

    def test_explain_picks_top_contributing_signal(self):
        f = feat_mod.compute({"price": 0.5, "volume_24h": 50_000, "volume_total": 60_000})
        out = predictor.predict(f)
        market = {"features": f, "signal_contribs": out["signal_contribs"]}
        text = predictor.explain(market)
        self.assertIsInstance(text, str)
        self.assertGreater(len(text), 0)


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------


class PairingTests(unittest.TestCase):
    def test_normalize_strips_filler_words(self):
        a = pairing.normalize_title("Will the Fed cut rates in June 2026?")
        b = pairing.normalize_title("Fed cuts rates June 2026")
        self.assertGreater(len(a), 5)
        self.assertGreater(len(b), 5)

    def test_finds_kalshi_polymarket_pair(self):
        markets = [
            {"platform": "Kalshi", "id": "K1", "title": "Will the Fed cut rates in June 2026?"},
            {"platform": "Polymarket", "id": "P1", "title": "Fed cuts rates in June 2026?"},
            {"platform": "Polymarket", "id": "P2", "title": "Will it rain tomorrow?"},
        ]
        pairs = pairing.find_pairs(markets)
        self.assertIn("K1", pairs)
        self.assertEqual(pairs["K1"][0], "P1")
        self.assertIn("P1", pairs)
        self.assertEqual(pairs["P1"][0], "K1")

    def test_no_pair_when_titles_dissimilar(self):
        markets = [
            {"platform": "Kalshi", "id": "K1", "title": "Will Trump win 2028?"},
            {"platform": "Polymarket", "id": "P1", "title": "Will it rain tomorrow?"},
        ]
        pairs = pairing.find_pairs(markets)
        self.assertEqual(pairs, {})


# ---------------------------------------------------------------------------
# Kalshi orderbook conversion
# ---------------------------------------------------------------------------


class KalshiOrderbookTests(unittest.TestCase):
    def test_yes_side_becomes_bids_no_side_inverts_to_asks(self):
        # Kalshi raw: yes bids at 55c size 100; no bids at 40c size 50
        raw = {"yes": [[55, 100]], "no": [[40, 50]]}
        book = kalshi._convert_orderbook(raw)
        self.assertEqual(len(book["bids"]), 1)
        self.assertEqual(len(book["asks"]), 1)
        self.assertAlmostEqual(book["bids"][0]["price"], 0.55)
        self.assertAlmostEqual(book["bids"][0]["size"], 100)
        # NO bid at 40 → YES ask at (100-40)/100 = 0.60
        self.assertAlmostEqual(book["asks"][0]["price"], 0.60)
        self.assertAlmostEqual(book["asks"][0]["size"], 50)

    def test_handles_empty_book(self):
        book = kalshi._convert_orderbook({})
        self.assertEqual(book["bids"], [])
        self.assertEqual(book["asks"], [])


# ---------------------------------------------------------------------------
# Polymarket normalize + token id extraction
# ---------------------------------------------------------------------------


class PolymarketNormalizeTests(unittest.TestCase):
    def test_extracts_yes_token_id(self):
        raw = {
            "id": "x",
            "conditionId": "0xdead",
            "question": "Will it rain?",
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.55", "0.45"]',
            "clobTokenIds": '["1234yes", "5678no"]',
            "slug": "rain",
        }
        out = polymarket.normalize(raw)
        self.assertEqual(out["book_key"], "1234yes")

    def test_prefers_event_slug(self):
        raw = {
            "id": "x",
            "question": "Who wins?",
            "slug": "candidate-x",
            "events": [{"slug": "race-2028"}],
        }
        out = polymarket.normalize(raw)
        self.assertEqual(out["url"], "https://polymarket.com/event/race-2028")


# ---------------------------------------------------------------------------
# Kalshi normalize
# ---------------------------------------------------------------------------


class KalshiNormalizeTests(unittest.TestCase):
    def test_cents_to_dollars_and_search_url(self):
        raw = {
            "ticker": "PRES-2028-DEM",
            "event_ticker": "PRES-2028",
            "title": "Will the Democrat win 2028?",
            "yes_bid": 55, "yes_ask": 57, "last_price": 56,
            "previous_yes_bid": 48, "volume_24h": 1_250_000, "volume": 9_000_000,
            "liquidity": 800_000,
        }
        out = kalshi.normalize(raw)
        self.assertAlmostEqual(out["price"], 0.56)
        self.assertAlmostEqual(out["price_change_24h"], 0.08)
        self.assertIn("search=PRES-2028", out["url"])
        self.assertEqual(out["book_key"], "PRES-2028-DEM")


# ---------------------------------------------------------------------------
# Snapshot logger (uses an isolated tempfile DB)
# ---------------------------------------------------------------------------


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        os.environ["SNAPSHOT_DB"] = self.tmp.name

    def tearDown(self):
        os.environ["SNAPSHOT_DB"] = ":memory:"
        try:
            os.unlink(self.tmp.name)
        except OSError:
            pass

    def test_record_and_read_back(self):
        market = {
            "platform": "Kalshi",
            "id": "K1",
            "title": "Test market",
            "price": 0.6,
            "yes_bid": 0.59,
            "yes_ask": 0.61,
            "volume_total": 100_000.0,
            "liquidity": 50_000.0,
            "features": {
                "spread": 0.02, "spread_pct": 0.033,
                "volume_24h": 25_000.0, "vol_share_24h": 0.25,
                "price_change_1h": 0.01, "price_change_24h": 0.05, "accel": 4.8,
                "book_bid_size": 1000, "book_ask_size": 500,
                "book_imbalance": 0.33, "book_depth_usd": 600,
                "has_book": True,
                "arb_gap": -0.05, "paired_platform": "Polymarket",
                "paired_id": "P1", "paired_similarity": 0.82,
            },
            "pre_move_score": 0.42,
            "direction": 0.31,
            "direction_label": "Lean UP",
        }
        n = snapshots.record_batch([market])
        self.assertEqual(n, 1)

        with sqlite3.connect(self.tmp.name) as conn:
            cur = conn.execute(
                "SELECT market_id, book_imbalance, pre_move_score, direction_label "
                "FROM market_snapshots"
            )
            rows = cur.fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "K1")
        self.assertAlmostEqual(rows[0][1], 0.33)
        self.assertAlmostEqual(rows[0][2], 0.42)
        self.assertEqual(rows[0][3], "Lean UP")

    def test_stats_reports_counts(self):
        markets = [
            {"platform": "K", "id": "A", "title": "t", "features": {}},
            {"platform": "K", "id": "B", "title": "t", "features": {}},
        ]
        snapshots.record_batch(markets)
        st = snapshots.stats()
        self.assertEqual(st["snapshots"], 2)
        self.assertEqual(st["markets_tracked"], 2)


if __name__ == "__main__":
    unittest.main()
