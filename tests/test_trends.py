"""Offline tests for the trend scorer and the API normalizers.

Run with: python -m unittest discover -s tests
"""
from __future__ import annotations

import unittest

from clients import kalshi, polymarket
from trends import classify_signal, compute_standout, explain


class StandoutScoreTests(unittest.TestCase):
    def test_quiet_market_scores_near_zero(self):
        m = {"price_change_24h": 0.001, "volume_24h": 5_000.0}
        out = compute_standout(m)
        self.assertLess(out["score"], 0.05)

    def test_big_mover_outranks_small_mover_at_same_volume(self):
        small = compute_standout({"price_change_24h": 0.02, "volume_24h": 50_000.0})
        big = compute_standout({"price_change_24h": 0.20, "volume_24h": 50_000.0})
        self.assertGreater(big["score"], small["score"])

    def test_higher_volume_lifts_score_for_same_move(self):
        low = compute_standout({"price_change_24h": 0.10, "volume_24h": 1_000.0})
        high = compute_standout({"price_change_24h": 0.10, "volume_24h": 1_000_000.0})
        self.assertGreater(high["score"], low["score"])

    def test_momentum_boosts_when_1h_aligns_with_24h(self):
        aligned = compute_standout(
            {"price_change_24h": 0.10, "price_change_1h": 0.02, "volume_24h": 10_000.0}
        )
        opposed = compute_standout(
            {"price_change_24h": 0.10, "price_change_1h": -0.02, "volume_24h": 10_000.0}
        )
        self.assertGreater(aligned["score"], opposed["score"])

    def test_downward_moves_score_same_as_upward(self):
        up = compute_standout({"price_change_24h": 0.15, "volume_24h": 20_000.0})
        down = compute_standout({"price_change_24h": -0.15, "volume_24h": 20_000.0})
        self.assertAlmostEqual(up["score"], down["score"])


class SignalClassificationTests(unittest.TestCase):
    def test_quiet_when_change_under_two_percent(self):
        self.assertEqual(classify_signal(0.01), "Quiet")

    def test_major_when_change_over_fifteen_percent(self):
        self.assertEqual(classify_signal(0.20), "Major move up")
        self.assertEqual(classify_signal(-0.18), "Major move down")

    def test_moving_in_between(self):
        self.assertEqual(classify_signal(0.08), "Moving up")
        self.assertEqual(classify_signal(-0.07), "Moving down")


class ExplanationTests(unittest.TestCase):
    def test_includes_direction_and_volume(self):
        text = explain(
            {
                "price_change_24h": 0.12,
                "volume_24h": 250_000.0,
                "momentum_factor": 1.4,
            }
        )
        self.assertIn("↑", text)
        self.assertIn("12.0%", text)
        self.assertIn("$250.0K", text)
        self.assertIn("building", text)

    def test_reversing_when_momentum_low(self):
        text = explain(
            {
                "price_change_24h": -0.05,
                "volume_24h": 2_000_000.0,
                "momentum_factor": 0.7,
            }
        )
        self.assertIn("↓", text)
        self.assertIn("reversing", text)


class KalshiNormalizeTests(unittest.TestCase):
    def test_cents_converted_to_dollars(self):
        raw = {
            "ticker": "PRES-2028-DEM",
            "event_ticker": "PRES-2028",
            "title": "Will the Democratic nominee win?",
            "yes_bid": 55,
            "yes_ask": 57,
            "last_price": 56,
            "previous_yes_bid": 48,
            "volume_24h": 1_250_000,  # cents
            "volume": 9_000_000,
            "liquidity": 800_000,
            "close_time": "2028-11-08T05:00:00Z",
        }
        out = kalshi.normalize(raw)
        self.assertEqual(out["platform"], "Kalshi")
        self.assertEqual(out["id"], "PRES-2028-DEM")
        self.assertAlmostEqual(out["price"], 0.56)
        self.assertAlmostEqual(out["yes_bid"], 0.55)
        self.assertAlmostEqual(out["price_change_24h"], 0.08)
        self.assertAlmostEqual(out["volume_24h"], 12_500.0)
        self.assertIn("kalshi.com/markets/pres-2028/pres-2028-dem", out["url"])

    def test_handles_missing_fields(self):
        out = kalshi.normalize({"ticker": "X"})
        self.assertEqual(out["price"], 0.0)
        self.assertEqual(out["price_change_24h"], 0.0)


class PolymarketNormalizeTests(unittest.TestCase):
    def test_parses_json_string_fields(self):
        raw = {
            "id": "abc",
            "conditionId": "0xdead",
            "question": "Will it rain tomorrow?",
            "slug": "will-it-rain",
            "outcomes": '["Yes", "No"]',
            "outcomePrices": '["0.72", "0.28"]',
            "volume24hr": "150000.50",
            "volume": "2500000",
            "liquidity": "80000",
            "oneDayPriceChange": "0.18",
            "oneHourPriceChange": "0.03",
            "bestBid": "0.71",
            "bestAsk": "0.73",
            "endDate": "2025-01-01T00:00:00Z",
        }
        out = polymarket.normalize(raw)
        self.assertEqual(out["platform"], "Polymarket")
        self.assertAlmostEqual(out["price"], 0.72)
        self.assertAlmostEqual(out["price_change_24h"], 0.18)
        self.assertAlmostEqual(out["price_change_1h"], 0.03)
        self.assertAlmostEqual(out["volume_24h"], 150000.50)
        self.assertEqual(out["url"], "https://polymarket.com/event/will-it-rain")

    def test_handles_already_parsed_outcomes(self):
        raw = {
            "id": "x",
            "question": "Test",
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.40", "0.60"],
        }
        out = polymarket.normalize(raw)
        self.assertAlmostEqual(out["price"], 0.40)

    def test_handles_garbage_gracefully(self):
        out = polymarket.normalize({"id": "x"})
        self.assertEqual(out["price"], 0.0)
        self.assertEqual(out["volume_24h"], 0.0)


if __name__ == "__main__":
    unittest.main()
