import asyncio
import os
from dotenv import load_dotenv
import argparse

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.data_ingestion.mexc_data_feed import MexcDataFeed
from libraries.order_management.chase_bba import ChaseBBA
from libraries.exchange_clients.coinex_exchange_client import CoinexExchangeClient

load_dotenv()

async def main(pair: str, amount_usd: float, minimum_bps_threshold: float):
  # instantiate feeds
  coinex_feed = CoinexDataFeed(pair)
  mexc_feed  = MexcDataFeed(pair)

  # schedule them
  task1 = asyncio.create_task(coinex_feed.run())
  task2 = asyncio.create_task(mexc_feed.run())

  access_id = os.getenv('COINEX_ACCESS_ID')
  secret_key = os.getenv('COINEX_SECRET_KEY')
  if not access_id or not secret_key:
    print("Access id or secret key for exchange client is incorrect")
    return

  coinex_exchange_client = CoinexExchangeClient(access_id, secret_key)

  # schedule your manager
  order_manager = ChaseBBA(pair, minimum_bps_threshold, coinex_feed, mexc_feed, coinex_exchange_client)
  task3 = asyncio.create_task(order_manager.run(amount_usd))

  # wait forever (or until one task ends)
  await asyncio.gather(task1, task2, task3)


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="Run spot arb order manager.")
  parser.add_argument("pair", type=str, help="Trading pair, e.g. PENDLE-USDT")
  parser.add_argument("amount_usd", type=float, help="Order amount in USD")
  parser.add_argument(
    "--minimum_bps_threshold", type=float, default=30,
    help="Minimum Arb bps spread to place orders (default: 30)"
  )

  args = parser.parse_args()

  asyncio.run(main(args.pair, args.amount_usd, args.minimum_bps_threshold))
