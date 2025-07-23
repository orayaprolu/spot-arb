import asyncio
import sqlite3
import os

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed

DB_DIR = "output"
DB_PATH = os.path.join(DB_DIR, "arb_data.db")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.executescript("""
CREATE TABLE IF NOT EXISTS bba (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  exchange TEXT NOT NULL,
  market TEXT NOT NULL,
  best_bid_price REAL NOT NULL,
  best_bid_size REAL NOT NULL,
  best_ask_price REAL NOT NULL,
  best_ask_size REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  exchange TEXT NOT NULL,
  market TEXT NOT NULL,
  taker_side TEXT NOT NULL,
  price REAL NOT NULL,
  amount REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orderbook (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  exchange TEXT NOT NULL,
  market TEXT NOT NULL,
  bids TEXT NOT NULL,
  asks TEXT NOT NULL
);
""")
conn.commit()

async def consume_bba(queue, exchange):
  while True:
    bba = await queue.get()
    cursor.execute(
      """
      INSERT INTO bba (ts, exchange, market, best_bid_price, best_bid_size, best_ask_price, best_ask_size)
      VALUES (?, ?, ?, ?, ?, ?, ?)
      """,
      (bba.ts.isoformat(), exchange, bba.market, bba.best_bid_price, bba.best_bid_size, bba.best_ask_price, bba.best_ask_size)
    )
    conn.commit()

async def consume_trades(queue, exchange):
  while True:
    trade = await queue.get()
    cursor.execute(
      """
      INSERT INTO trades (ts, exchange, market, taker_side, price, amount)
      VALUES (?, ?, ?, ?, ?, ?)
      """,
      (trade.ts.isoformat(), exchange, trade.market, trade.taker_side.name, trade.price, trade.amount)
    )
    conn.commit()

import json

async def consume_orderbook(queue, exchange):
  while True:
    ob = await queue.get()

    bids_json = json.dumps(ob.bids)  # List of (price, size)
    asks_json = json.dumps(ob.asks)

    cursor.execute(
      """
      INSERT INTO orderbook (ts, exchange, market, bids, asks)
      VALUES (?, ?, ?, ?, ?)
      """,
      (ob.ts.isoformat(), exchange, ob.market, bids_json, asks_json)
    )
    conn.commit()


# Launch for one pair
async def run_pair(pair: str):
  feed = CoinexDataFeed(pair)
  task1 = asyncio.create_task(feed.run())
  task2 = asyncio.create_task(consume_bba(feed.bba_queue, exchange=feed.exchange))
  task3 = asyncio.create_task(consume_trades(feed.trade_queue, exchange=feed.exchange))
  task4 = asyncio.create_task(consume_orderbook(feed.orderbook_queue, exchange=feed.exchange))
  return [task1, task2, task3, task4]

# Entry point: run all pairs forever
async def main():
  PAIRS = ["BTT-USDT", "XEC-USDT", "PENDLE-USDT"]
  all_tasks = []
  for pair in PAIRS:
    tasks = await run_pair(pair)
    all_tasks.extend(tasks)

  # Run everything forever
  await asyncio.gather(*all_tasks)

if __name__ == "__main__":
  asyncio.run(main())
