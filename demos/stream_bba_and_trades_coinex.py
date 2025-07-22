import asyncio
import argparse


from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed

async def consume_bba(queue):
  while True:
    bba = await queue.get()
    print(f"[BBA] {bba.ts} | {bba.market} | bid: {bba.best_bid_price:.5f} x {bba.best_bid_size:.2f} | ask: {bba.best_ask_price:.5f} x {bba.best_ask_size:.2f}")

async def consume_trades(queue):
  while True:
    trade = await queue.get()
    print(f"[TRADE] {trade.ts} | {trade.market} | {trade.taker_side.name} | {trade.amount:.2f} @ {trade.price:.5f}")

async def main(pair: str):
  feed = CoinexDataFeed(pair)
  asyncio.create_task(feed.run())

  asyncio.create_task(consume_bba(feed.bba_queue))
  asyncio.create_task(consume_trades(feed.trade_queue))


  await asyncio.sleep(5)
  while True:
    await asyncio.sleep(3600)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("--pair", type=str, required=False, help="Trading pair (e.g. BTC-USDT)")
  args = parser.parse_args()

  pair = args.pair if args.pair else "BTC-USDT"
  asyncio.run(main(pair))
