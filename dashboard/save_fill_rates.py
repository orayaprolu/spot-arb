from datetime import datetime
from typing import List
import asyncio
import csv

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.models.trade import Trade
from libraries.models.side import Side

async def record_fills(pair: str, feed: CoinexDataFeed, interval_sec: int = 900):
  while True:
    await asyncio.sleep(interval_sec)

    trades: List[Trade] = []
    while feed.trade_queue:
      trades.append(feed.trade_queue[0])
      feed.trade_queue.popleft()

    best_bid = feed.get_best_bid()
    if best_bid is None:
      continue

    fills = [
      trade for trade in trades
      if trade.taker_side == Side.SELL and trade.price <= best_bid
    ]

    total_volume = sum(trade.amount for trade in fills)
    total_volume_usdt = sum(trade.amount * trade.price for trade in fills)

    timestamp = datetime.utcnow().isoformat()

    row = [timestamp, pair, total_volume,f"${total_volume_usdt}"]
    print(row)
    with open(f"./output/fill_rates/{pair.replace('-', '_')}_fills.csv", mode='a', newline='') as f:
      writer = csv.writer(f)
      writer.writerow(row)

async def main(pairs: List[str]):
  feeds = {pair: CoinexDataFeed(pair) for pair in pairs}

  for feed in feeds.values():
    asyncio.create_task(feed.run())

  for pair, feed in feeds.items():
    asyncio.create_task(record_fills(pair, feed))

  await asyncio.Event().wait()


if __name__ == "__main__":
  symbols = ["XEC-USDT", "PENDLE-USDT", "BTT-USDT", "ORDI-USDT", "LUNC-USDT"]
  asyncio.run(main(symbols))
