import asyncio
import os
from dotenv import load_dotenv

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.data_ingestion.mexc_data_feed import MexcDataFeed
from libraries.order_management.chase_bba import ChaseBBA
from libraries.exchange_clients.coinex_exchange_client import CoinexExchangeClient

load_dotenv()

async def main(pair: str):
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
  order_manager = ChaseBBA(pair, coinex_feed, mexc_feed, coinex_exchange_client)
  task3 = asyncio.create_task(order_manager.run(500))

  # wait forever (or until one task ends)
  await asyncio.gather(task1, task2, task3)


if __name__ == "__main__":
  asyncio.run(main("PENDLE-USDT"))
