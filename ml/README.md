# Training an ML predictor from logged snapshots

Every dashboard refresh writes one row per market to `snapshots.db` with
the exact feature vector the heuristic predictor uses. Once you've
accumulated a few weeks of data, you have a labeled dataset for free:
join each snapshot to the *future* price of the same market and label
whether a meaningful move actually happened.

## Schema

See `snapshots.py` — the `market_snapshots` table has columns for:

- Identity: `market_id`, `platform`, `title`, `ts`
- Market state: `price`, `yes_bid`, `yes_ask`, `spread`, `volume_24h`,
  `volume_total`, `liquidity`
- Features (the inputs your model will learn from):
  `vol_share_24h`, `price_change_1h`, `price_change_24h`, `accel`,
  `book_bid_size`, `book_ask_size`, `book_imbalance`, `book_depth_usd`,
  `arb_gap`, `paired_similarity`
- Current prediction (for comparison vs your trained model):
  `pre_move_score`, `direction`, `direction_label`

## Labeling future moves

To label "did the price move more than 5 percentage points in the next
2 hours after this snapshot", run something like:

```sql
WITH future AS (
    SELECT
        s.id AS snapshot_id,
        s.market_id,
        s.ts AS t0,
        s.price AS p0,
        (
            SELECT price FROM market_snapshots f
            WHERE f.market_id = s.market_id
              AND f.ts BETWEEN s.ts + 7200 AND s.ts + 10800   -- 2-3h ahead
            ORDER BY f.ts ASC
            LIMIT 1
        ) AS p_future
    FROM market_snapshots s
)
SELECT
    snapshot_id,
    p0,
    p_future,
    CASE WHEN ABS(p_future - p0) >= 0.05 THEN 1 ELSE 0 END AS moved,
    CASE WHEN p_future - p0 >= 0.05 THEN 1
         WHEN p_future - p0 <= -0.05 THEN -1
         ELSE 0 END AS direction
FROM future
WHERE p_future IS NOT NULL;
```

Pick whatever window and threshold matches the trading horizon you care
about (1h / 6h / 24h ahead; ±2% / ±5% / ±10%).

## Suggested training flow

1. **Export** the joined dataset to a DataFrame:
   ```python
   import sqlite3, pandas as pd
   conn = sqlite3.connect("snapshots.db")
   df = pd.read_sql_query("SELECT * FROM market_snapshots", conn)
   ```

2. **Compute labels** with the SQL above (or in pandas with `groupby` +
   `shift` along `ts` per market).

3. **Pick features** — the columns that already feed the heuristic:
   ```python
   FEATURES = [
       "vol_share_24h", "price_change_1h", "price_change_24h", "accel",
       "spread", "spread_pct",
       "book_imbalance", "book_bid_size", "book_ask_size", "book_depth_usd",
       "arb_gap", "paired_similarity",
       "price",
   ]
   ```

4. **Train**. Two reasonable starting points:
   - **Magnitude classifier**: binary — did the market move ≥ X% in the
     next window? Gradient-boosted trees (`xgboost`, `lightgbm`) handle
     mixed-scale features well without normalization.
   - **Direction classifier**: 3-class — up / flat / down. Same feature
     set; use class-balanced sample weights.

5. **Backtest properly**: split by *time*, not randomly. Train on the
   first 70% of timestamps, validate on the last 30%. Otherwise leakage
   from future snapshots of the same market will inflate metrics.

6. **Compare** against the heuristic `pre_move_score` as a baseline — if
   your model can't beat it on held-out time, the heuristic is fine.

## Plumbing the trained model back in

Once you have a model artifact, wire it in beside the heuristic by
exporting one function from a new `ml_predictor.py`:

```python
def predict(feats: dict) -> dict:
    x = np.array([[feats[c] for c in FEATURES]])
    return {
        "pre_move_score": float(model.predict_proba(x)[0, 1]),
        "direction": float(direction_model.predict(x)[0]),
        ...
    }
```

Then in `app.py`, replace `predictor.predict(f)` with whichever
implementation you want, or blend both.
