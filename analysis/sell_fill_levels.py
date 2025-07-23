import sqlite3
import json
from datetime import datetime, timedelta, timezone
from collections import Counter
import matplotlib.pyplot as plt

# --- Config ---
DB_PATH = "output/arb_data.db"
PAIR = "PENDLEUSDT"
HOURS_BACK = 24

# --- Connect DB ---
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cutoff_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=HOURS_BACK)).isoformat()

# --- Fetch taker sell trades ---
cursor.execute("""
SELECT ts, amount, price
FROM trades
WHERE market = ? AND taker_side = 'SELL' AND ts >= ?
ORDER BY ts ASC
""", (PAIR, cutoff_ts))
trades = cursor.fetchall()

print(f"Found {len(trades)} taker sell trades in last {HOURS_BACK} hours.")

# --- Match each sell to order book and simulate fills ---
level_fill_counts = Counter()

for ts, amount, price in trades:
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

    try:
        bids = json.loads(row[0])  # [[price, size], ...]
    except json.JSONDecodeError:
        continue

    remaining = amount

    for level_price, level_size in bids:
        if remaining <= 0:
            break
        fill_size = min(remaining, level_size)
        level_fill_counts[float(level_price)] += fill_size
        remaining -= fill_size

conn.close()

# --- Plot the fill breakdown ---
if not level_fill_counts:
    print("No matching order books found. Nothing to plot.")
else:
    prices = sorted(level_fill_counts.keys(), reverse=True)
    sizes = [level_fill_counts[p] for p in prices]

    plt.figure(figsize=(12, 6))
    plt.bar(prices, sizes, width=0.002)
    plt.xlabel("Price Level (USDT)")
    plt.ylabel("Total Size Sold")
    plt.title(f"Taker Sell Fill Distribution by Level - Last {HOURS_BACK} Hours")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
