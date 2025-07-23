import json
import websockets
import asyncio
from datetime import datetime, timezone
import gzip
from typing import override
import traceback

from libraries.data_ingestion.base_data_feed import BaseDataFeed
from libraries.models.bba import BBA
from libraries.models.side import Side
from libraries.models.trade import Trade
from libraries.models.orderbook import Orderbook

COINEX_WS = "wss://socket.coinex.com/v2/spot"

class CoinexDataFeed(BaseDataFeed):
  '''
  This class automatically gets the CoinEx BBA for a pair and keeps the websocket connection alive.
  All you need to do is call the run function as a background task and whenever you need the best_bid call the get_best_bid getter.
  (Or manually access the BBA object)
  '''
  def __init__(self, pair: str):
    self.exchange = "CoinEx"
    self.pair = pair.replace('-', '')
    self.ws_url = COINEX_WS
    self.ws = None
    self.bba_queue: asyncio.Queue[BBA] = asyncio.Queue()
    self.trade_queue: asyncio.Queue[Trade] = asyncio.Queue()
    self.orderbook_queue: asyncio.Queue[Orderbook] = asyncio.Queue()
    self.last_msg_time = datetime.now(tz=timezone.utc)

  async def _connect_websocket(self):
    try:
      self.ws = None
      self.ws = await websockets.connect(uri=self.ws_url, compression=None, ping_interval=None)
      print(f"[CONNECTED {self.exchange}] Connected to WS")
      return True

    except Exception as e:
      print(f"[ERROR {self.exchange}] Failed to connect to CoinEx WS or subscribe to BBA channel: {e}")
      return False

  async def _subscribe_bba(self) -> bool:
    if not self.ws:
      await self._connect_websocket()

    sub_msg = {
      "method": "bbo.subscribe",
      "params": {
        "market_list": [self.pair]
      },
      "id": 1
    }

    try:
      if self.ws:
        await self.ws.send(json.dumps(sub_msg))
        await self.ws.recv()
        print(f"[SUBSCRIBED {self.exchange}] Subscribed to BBA channel")
        return True

    except Exception as e:
      print(f"[ERROR {self.exchange}] Failed to connect to CoinEx WS or subscribe to BBA channel: {e}")
      return False

    print("Shouldn't get here")
    return False

  async def _subscribe_trades(self) -> bool:
    if not self.ws:
      await self._connect_websocket()

    sub_msg = {
      "method": "deals.subscribe",
      "params": {
        "market_list": [self.pair]
      },
      "id": 1
    }

    try:
      if self.ws:
        await self.ws.send(json.dumps(sub_msg))
        await self.ws.recv()
      print(f"[SUBSCRIBED {self.exchange}] Subscribed to Trades channel")
      return True

    except Exception as e:
      print(f"[ERROR {self.exchange}] Failed to connect to CoinEx WS or subscribe to Trades channel: {e}")
      return False

  async def _subscribe_depth(self) -> bool:
    if not self.ws:
      await self._connect_websocket()

    sub_msg = {
      "method": "depth.subscribe",
      "params": {
        "market_list": [[self.pair, 5, "0", True]]  # 10 levels, no price merge, full depth
      },
      "id": 1
    }

    try:
      if self.ws:
        await self.ws.send(json.dumps(sub_msg))
        await self.ws.recv()
      print(f"[SUBSCRIBED {self.exchange}] Subscribed to Depth channel")
      return True

    except Exception as e:
      print(f"[ERROR {self.exchange}] Failed to subscribe to Depth channel: {e}")
      return False

  @override
  async def _ping(self):
    if not self.ws:
      print("[ERROR] No CoinEx Websocket connection found")
      return

    param = {"method": "server.ping", "params": {}, "id": 1}
    while True:
      await self.ws.send(json.dumps(param))
      await asyncio.sleep(3)

  async def _streamer(self):
    if not self.ws:
      print("[ERROR] No CoinEx Websocket connection found")
      return

    async for raw in self.ws:
      self.last_msg_time = datetime.now(tz=timezone.utc)
      if isinstance(raw, str):
        continue
      decompressed = gzip.decompress(raw).decode('utf-8')
      data = json.loads(decompressed)
      if data.get("method") == "bbo.update":
        await self._stream_bba(data)
      elif data.get("method") == "deals.update":
        await self._stream_trades(data)
      elif data.get("method") == "depth.update":
        await self._stream_depth(data)

  async def _stream_bba(self, data):
    payload = data.get("data")
    unix_ts = float(payload.get("updated_at"))
    ts = datetime.fromtimestamp(unix_ts / 1000, tz=timezone.utc)
    best_bid_price = float(payload.get("best_bid_price"))
    best_bid_size = float(payload.get("best_bid_size"))
    best_ask_price = float(payload.get("best_ask_price"))
    best_ask_size = float(payload.get("best_ask_size"))

    bba = BBA(
      ts = ts,
      market = self.pair,
      best_bid_price = best_bid_price,
      best_bid_size = best_bid_size,
      best_ask_price = best_ask_price,
      best_ask_size = best_ask_size,
    )

    await self.bba_queue.put(bba)

  async def _stream_trades(self, data):
    payload = data.get("data")
    market = payload["market"]
    for trade in payload["deal_list"]:
      unix_ts = float(trade["created_at"])
      ts = datetime.fromtimestamp(unix_ts / 1000, tz=timezone.utc)
      taker_side = Side.BUY if trade["side"] == 'buy' else Side.SELL
      price = float(trade["price"])
      amount = float(trade["amount"])

      trade = Trade(
        ts = ts,
        market = market,
        taker_side = taker_side,
        price = price,
        amount = amount
      )

      await self.trade_queue.put(trade)

  async def _stream_depth(self, data):
    payload = data.get("data")
    depth = payload.get("depth")
    unix_ts = float(depth["updated_at"])
    ts = datetime.fromtimestamp(unix_ts / 1000, tz=timezone.utc)
    market = payload.get("market")

    bids = [(float(price), float(size)) for price, size in depth.get("bids", [])]
    asks = [(float(price), float(size)) for price, size in depth.get("asks", [])]

    orderbook = Orderbook(
      ts=ts,
      market=market,
      bids=bids,
      asks=asks,
    )

    await self.orderbook_queue.put(orderbook)

  @override
  async def run(self):
    """Connect, then keep reading & pinging until the socket dies then reconnects."""
    while True:
      # Sub to websockets
      success_bba = await self._subscribe_bba()
      success_trades = await self._subscribe_trades()
      success_depth = await self._subscribe_depth()

      if not success_bba or not success_trades or not success_depth:
        raise RuntimeError(f"[FATAL {self.exchange}] Failed to subscribe to required channels")

      # Create background tasks
      ping_task = asyncio.create_task(self._ping())
      reader_task = asyncio.create_task(self._streamer())

      # Run for one hour or until task fails, then restart
      try:
        done, _ = await asyncio.wait(
          [ping_task, reader_task],
          timeout=3600,
          return_when=asyncio.FIRST_EXCEPTION
        )

        for task in done:
          if task.exception():
            print(f"[ERROR {self.exchange}] Task failed with: {task.exception()}")
            exc = task.exception()
            if exc:
              traceback.print_exception(type(exc), exc, exc.__traceback__)
      finally:
        print(f"[INFO {self.exchange}] Reconnecting WebSocket...")
        if self.ws:
          await self.ws.close() # type: ignore[optional]
        self.ws = None
        ping_task.cancel()
        reader_task.cancel()
        await asyncio.sleep(2)

async def consume_bba(queue):
  while True:
    bba = await queue.get()
    print(f"[BBA] {bba.ts} | {bba.market} | bid: {bba.best_bid_price:.5f} x {bba.best_bid_size:.2f} | ask: {bba.best_ask_price:.5f} x {bba.best_ask_size:.2f}")

async def consume_trades(queue):
  while True:
    trade = await queue.get()
    print(f"[TRADE] {trade.ts} | {trade.market} | {trade.taker_side.name} | {trade.amount:.2f} @ {trade.price:.5f}")

async def consume_orderbook(queue):
  while True:
    ob = await queue.get()
    top_bid = ob.bids[0] if ob.bids else (0, 0)
    top_ask = ob.asks[0] if ob.asks else (0, 0)
    print(f"[ORDERBOOK] {ob.ts} | {ob.market} | bid: {top_bid} | ask: {top_ask}")

async def main():
  feed = CoinexDataFeed("XEC-USDT")
  asyncio.create_task(feed.run())

  asyncio.create_task(consume_bba(feed.bba_queue))
  asyncio.create_task(consume_trades(feed.trade_queue))
  asyncio.create_task(consume_orderbook(feed.orderbook_queue))


  await asyncio.sleep(5)
  while True:
    await asyncio.sleep(3600)

if __name__ == "__main__":
  asyncio.run(main())
