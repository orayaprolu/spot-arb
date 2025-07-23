import sqlite3
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import pandas as pd

# --- Config ---
DB_PATH = "output/arb_data.db"
PAIR = "PENDLEUSDT"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- Setup ---
cutoff_ts = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat()

# Step 1: Fetch trades (SELL side) in the last 24h
cursor.execute("""
SELECT ts, amount, price
FROM trades
WHERE market = ? AND taker_side = 'SELL' AND ts >= ?
ORDER BY ts ASC
""", (PAIR, cutoff_ts))
trades = cursor.fetchall()

# Initialize aggregators
total_usd_filled = 0.0
total_overflow_usd = 0.0
per_hour_fills = defaultdict(float)
per_hour_overflow = defaultdict(float)

# Step 2: For each trade, compute overflow and aggregate by hour
for ts, amount, price in trades:
    # Get matching BBA
    cursor.execute("""
    SELECT best_bid_size
    FROM bba
    WHERE market = ? AND ts <= ?
    ORDER BY ts DESC
    LIMIT 1
    """, (PAIR, ts))
    row = cursor.fetchone()
    best_bid_size = row[0] if row else 0.0

    overflow_amt = max(0.0, amount - best_bid_size)
    usd_filled = amount * price
    overflow_usd = overflow_amt * price

    total_usd_filled += usd_filled
    total_overflow_usd += overflow_usd

    # Group by hour
    hour_key = ts[:13]  # 'YYYY-MM-DDTHH'
    per_hour_fills[hour_key] += usd_filled
    per_hour_overflow[hour_key] += overflow_usd

# Convert to DataFrame for nicer display
df = pd.DataFrame([
    {
        "hour": hour,
        "usd_filled": per_hour_fills[hour],
        "overflow_usd": per_hour_overflow[hour]
    }
    for hour in sorted(per_hour_fills)
])

# Average overflow per hour
num_hours = len(per_hour_overflow)
avg_overflow_per_hour = total_overflow_usd / num_hours if num_hours > 0 else 0.0


print(f"\nTotal USD filled (taker sells): ${total_usd_filled:,.2f}")
print(f"Total overflow past best bid (USD): ${total_overflow_usd:,.2f}\n")
print(f"Average overflow USD per active hour: ${avg_overflow_per_hour:.2f}")
print(df)

conn.close()
