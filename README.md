# Betting Trend Spotter

A small Flask app that pulls live markets from **Kalshi** and **Polymarket** and surfaces the ones that are *standing out* — markets where a meaningful price move is being backed by real trading volume.

The idea: when informed traders start pricing in new information, the market moves before the news does. This app ranks every active market by a combined "standout score" so you can quickly see what's catching a bid.

## What the score means

For each market we compute:

```
score = |24h price change|  ×  log10(24h volume + 10)  ×  momentum
```

- **24h price change** — the core signal: how much the market re-priced today.
- **24h volume** — log-scaled, so $1M moves matter more than $1K moves without one whale market dominating the leaderboard.
- **Momentum** — boost (×1.4) if the last hour is moving the same direction as the last 24h, discount (×0.7) if the move is reversing. Only applies when 1h data is available (Polymarket).

A signal badge labels each market by 24h move size:

| Badge | 24h move |
| --- | --- |
| `Quiet` | < 2% |
| `Slight` | 2–5% |
| `Moving` | 5–15% |
| `Major move` | ≥ 15% |

## Running it

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5050>.

The dashboard auto-refreshes every minute. Server-side, the upstream APIs are cached for 60 seconds to stay polite.

### Filters

- **Platform** — Kalshi, Polymarket, or both
- **Min 24h Volume** — hides illiquid markets where moves are just noise
- **Min 24h Move (%)** — hides flat markets
- **Show** — Top 25 / 50 / 100

## Tests

```bash
python -m unittest discover -s tests
```

The tests cover the scoring math and the per-platform schema normalizers, so they run fully offline.

## Project layout

```
.
├── app.py                  # Flask app + /api/trends endpoint
├── clients/
│   ├── kalshi.py           # Kalshi /markets fetcher + normalizer
│   └── polymarket.py       # Polymarket Gamma API fetcher + normalizer
├── trends.py               # standout score, signal classifier, explanation text
├── templates/index.html    # dashboard
├── static/                 # JS + CSS
├── tests/test_trends.py
└── requirements.txt
```

## Notes & caveats

- Kalshi's `/markets` list exposes `previous_yes_bid` as the closest 24h baseline — for sub-day resolution you'd need to pull candlesticks per ticker.
- Polymarket exposes `oneDayPriceChange` and `oneHourPriceChange` directly, so momentum scoring is richer there.
- Both APIs are public/read-only here. No keys, no orders are placed, no trades are made. This is a research tool, not investment advice.
