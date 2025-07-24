import sqlite3
from datetime import datetime, timedelta, timezone
import matplotlib.pyplot as plt
import json
from collections import defaultdict

# --- Config ---
DB_PATH = "output/arb_data.db"
PAIR = "XECUSDT"
FILTER_THRESHOLD = 0.95  # only count BBA trades consuming ≥95% of visible size

# --- Connect ---
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- Time cutoff ---
cutoff_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat()

# --- Step 1: Fetch sell trades ---
cursor.execute("""
SELECT ts, amount, price
FROM trades
WHERE market = ? AND taker_side = 'SELL' AND ts >= ?
ORDER BY ts ASC
""", (PAIR, cutoff_ts))
trades = cursor.fetchall()

# --- Step 2: Compute USD fill per level, skipping shallow BBA trades ---
usd_fill_by_level = defaultdict(float)

for ts, amount, trade_price in trades:
    # Get orderbook snapshot before the trade
    cursor.execute("""
    SELECT bids
    FROM orderbook
    WHERE market = ? AND ts <= ?
    ORDER BY ts DESC
    LIMIT 1
    """, (PAIR, ts))
    row = cursor.fetchone()
    if not row:
        continue

    bids = json.loads(row[0])  # list of [price, size]
    best_bid_price, best_bid_size = bids[0]

    # Skip BBA trades that didn't consume at least FILTER_THRESHOLD of visible size
    if trade_price >= best_bid_price and amount < FILTER_THRESHOLD * best_bid_size:
        continue

    # Determine depth (levels below BBA)
    depth = 0
    for level_price, level_size in bids:
        if trade_price >= level_price:
            break
        depth += 1

    usd_fill_by_level[depth] += amount * trade_price

conn.close()

# --- Step 3: Visualize USD fill per level ---
levels = sorted(usd_fill_by_level.keys())
usd_values = [usd_fill_by_level[level] for level in levels]

plt.figure(figsize=(10, 5))
plt.bar(levels, usd_values, color='mediumseagreen', edgecolor='black')
plt.title(f"USD Filled at Each Order Book Level (Filtered BBA < {int(FILTER_THRESHOLD*100)}% of visible)")
plt.xlabel("Levels Below Best Bid")
plt.ylabel("Total USD Filled")
plt.xticks(levels)
plt.grid(True)
plt.tight_layout()
plt.show()
