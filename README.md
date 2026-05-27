# Betting Trend Predictor

A live dashboard that watches Kalshi and Polymarket for **markets about to move** — not markets that already moved. Each market is scored on four pre-move signals drawn from order-flow microstructure and cross-platform arbitrage. The same feature vector is logged to SQLite so you can train a real ML model on it later.

## What it does

For every active market on both platforms, the app computes:

| Signal | What it measures | Why it's predictive |
| --- | --- | --- |
| **Order-book imbalance** | Top-5 bid size vs ask size on the YES book | Money already lined up to push price one way before any trade prints |
| **Volume acceleration** | 24h volume as a share of lifetime volume | Money flowing in lately — sign of news or accumulation |
| **Momentum acceleration** | Last-hour move vs trailing 24h hourly average | A trend that's speeding up, not coasting |
| **Cross-platform divergence** | Same event priced X¢ apart on Kalshi vs Polymarket | Laggard tends to converge to leader within hours |

The signals are clipped, weighted, and summed into a **pre-move score** in `[0, 1]` and a **direction** in `[-1, +1]` (negative = down bias, positive = up bias). The score's contributors are exposed per market so you can see *which* signal is driving the rank.

## What it doesn't do

This is a **heuristic predictor**, not a backtested ML model. The weights are starting points calibrated from microstructure intuition, not empirical accuracy on historical data. To get to a real ML model, see [`ml/README.md`](ml/README.md) — the app logs every snapshot to SQLite so you can label future moves and train from your own data.

## Running it

```bash
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5050>.

Optional env vars:
- `SNAPSHOT_DB=/path/to/file.db` — where to log snapshots (default `./snapshots.db`, use `:memory:` to disable)

## Filters

- **Platform**: Kalshi / Polymarket / both
- **Direction**: Up bias / Down bias / Any
- **Min 24h Volume**: filter out illiquid markets
- **Min Pre-Move Score**: floor on the signal strength

## API endpoints

- `GET /api/predictions?platform=&direction=&min_vol=&min_score=&limit=` — ranked predictions JSON
- `GET /api/snapshots/stats` — count & timespan of logged snapshots

## Tests

```bash
python -m unittest discover -s tests
```

Tests cover feature extraction, predictor scoring + direction, fuzzy pairing, Kalshi orderbook conversion, Polymarket token-id extraction, and the snapshot SQLite logger — all offline.

## Project layout

```
.
├── app.py                  # Flask app, orchestration
├── clients/
│   ├── kalshi.py           # /markets + /orderbook
│   └── polymarket.py       # gamma /markets + clob /book + tokenId extraction
├── features.py             # feature vector per market
├── pairing.py              # fuzzy cross-platform title match
├── predictor.py            # heuristic score + direction + signal contribs
├── snapshots.py            # SQLite logger for future ML training
├── ml/README.md            # how to train a real model from logged data
├── templates/index.html
├── static/                 # app.js + style.css
├── tests/test_predictor.py
└── requirements.txt
```

## Important caveats

- **Heuristic, not trained.** Signal weights are educated guesses, not optimized.
- **Order books only fetched for top-30 by volume per platform** to keep API usage reasonable. Tail markets won't have an imbalance signal.
- **Cross-platform pairing is title-based fuzzy matching.** It catches obvious pairs (rate decisions, elections, sports) but misses paraphrased titles. Inspect the "paired with" line on each card to sanity-check matches.
- **Not investment advice.** Pre-move signals raise probabilities; they don't guarantee outcomes. Markets can stay irrational longer than your bankroll can stay solvent.
