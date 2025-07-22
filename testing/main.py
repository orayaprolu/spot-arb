import asyncio
import os
import signal
import sys

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.data_ingestion.mexc_data_feed import MexcDataFeed
from libraries.exchange_clients.coinex_exchange_client import CoinexExchangeClient
from libraries.execution_logic.laddering import make_buy_ladder
from dotenv import load_dotenv

from utils.consume_stream import consume_stream
from utils.difference_in_bps import difference_in_bps

load_dotenv()

BPS_THRESHOLD = 26

async def periodic_restart(interval_s: float):
    await asyncio.sleep(interval_s)
    print(f"[Supervisor] {interval_s}s elapsed, restarting now…")
    # clean shutdown
    os.kill(os.getpid(), signal.SIGINT)

async def feed_supervisor(feed, name):
  while True:
    try:
      print(f"[{name}] connecting…")
      await feed.run()      # will only return on real disconnect
    except Exception as e:
      print(f"[{name}] crashed:", e)
    print(f"[{name}] reconnecting in 2 minutes")
    await asyncio.sleep(120)

async def main(pair: str, size_usdt: float):

  asyncio.create_task(periodic_restart(3600))

  coinex_data_feed = CoinexDataFeed(pair)
  mexc_data_feed = MexcDataFeed(pair)

  coinex_exchange_client = CoinexExchangeClient(os.environ['COINEX_ACCESS_ID'], os.environ['COINEX_SECRET_KEY'])

  # start supervisors for running feed objects
  asyncio.create_task(feed_supervisor(coinex_data_feed, "CoinEx"))
  asyncio.create_task(feed_supervisor(mexc_data_feed,  "MEXC"))

  await asyncio.sleep(2)

# drains feed so bba stays fresh
  asyncio.create_task(consume_stream(coinex_data_feed))
  asyncio.create_task(consume_stream(mexc_data_feed))

  while True:
    await asyncio.sleep(1) # Waits for a second to let consume stream start
    coinex_bba = coinex_data_feed.bba
    mexc_bba = mexc_data_feed.bba

    if coinex_bba is None or mexc_bba is None:
      print("somenow none", coinex_bba, mexc_bba)
      continue


    bps = difference_in_bps(coinex_bba.bid, mexc_bba.bid)
    print("Arb in BPS", bps, "CoinEx", coinex_bba.bid, "MexC", mexc_bba.bid)

    amount = size_usdt / coinex_bba.bid
    if bps > BPS_THRESHOLD:
      buy_ladder = make_buy_ladder(coinex_bba.bid, amount, taper_ratio = 0.5)
    else:
      anchor_bid = coinex_bba.bid * (1 - BPS_THRESHOLD / 10_000)
      buy_ladder = make_buy_ladder(anchor_bid, amount, taper_ratio = 0.5)

    for limit_price, size in buy_ladder:
      coinex_exchange_client.place_order(
        pair = pair,
        side = "buy",
        amount = size,
        price = limit_price,
        ccy = "USDT"
      )
    print("Placed ladder order from", coinex_bba.bid)
    await asyncio.sleep(1)
    print("Canceling orders")
    coinex_exchange_client.cancel_all_orders(pair)

if __name__=="__main__":
  try:
    asyncio.run(main("XEC-USDT", size_usdt=1000))
  except KeyboardInterrupt:
    sys.exit(1)
    print("[Main] Received SIGINT, exiting…")




# PENDLE Arb over many hours: ~30bps
# MexC Taker Fee : 4 bps
# CoinEx Maker Fee : 12.8 bps
# Convergence Risk: 2 bps (Not high since we are doing buy illiquid)
# Inventory Holding Risk: 1 bps (Pretty much non existent, PENDLE seemes stable and market risk balaneces over time)
# USDT Transfer fee: 1 bps
#
# Inventory Threshold Risk ~$800 position (I think please recalculate, $1 transfer fee)
# Total Arb: 30 - 4 - 12.8 - 2 - 1 - 1 = 9.2 bps (Transfer time for PENDLE is about 4 minutes)
