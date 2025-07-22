import asyncio

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.data_ingestion.mexc_data_feed import MexcDataFeed

from utils.difference_in_bps import difference_in_bps


async def main(pair: str):
  coinex_feed = CoinexDataFeed(pair)
  mexc_feed = MexcDataFeed(pair)

  asyncio.create_task(coinex_feed.run())
  asyncio.create_task(mexc_feed.run())
  await asyncio.sleep(10)

  while True:
    await asyncio.sleep(2)
    coinex_bid = coinex_feed.get_best_bid()
    mexc_bid = mexc_feed.get_best_bid()
    if coinex_bid and mexc_bid:
      arb_bps = difference_in_bps(coinex_bid, mexc_bid)
      print(arb_bps, coinex_bid, mexc_bid)

if __name__ == '__main__':
  asyncio.run(main("BTT-USDT"))
