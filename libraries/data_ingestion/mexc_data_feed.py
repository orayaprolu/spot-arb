from datetime import datetime
import websockets
import json
import asyncio
from typing import override, Optional

from libraries.models.bba import BBA
from libraries.data_ingestion.base_data_feed import BaseDataFeed
from protos.PushDataV3ApiWrapper_pb2 import PushDataV3ApiWrapper # type: ignore

MEXC_WS = "wss://wbs-api.mexc.com/ws"
PARTIAL_DEPTH_WS_ENDPOINT = "spot@public.aggre.bookTicker.v3.api.pb@100ms"

class MexcDataFeed(BaseDataFeed):
  def __init__(self, pair: str):
    self.exchange = "MexC"
    self.ws_url = MEXC_WS
    self.pair = pair.replace('-', '')
    self.ws = None
    self.bba = None

  async def _subscribe_depth(self) -> bool:
    channel = f"{PARTIAL_DEPTH_WS_ENDPOINT}@{self.pair}"
    sub_msg = {"method": "SUBSCRIPTION", "params": [channel]}

    try:
      self.ws = await websockets.connect(self.ws_url, ping_interval=None)
      await self.ws.send(json.dumps(sub_msg))
      return True

    except Exception as e:
      print(f"[ERROR] Failed to connect or subscribe: {e}")
      return False

  @override
  async def _ping(self):
    async def ping_event() -> bool:
      if not self.ws:
        print("[ERROR] No Websocket connection found in _ping")
        return False

      ping_msg = {"method": "PING"}
      await self.ws.send(json.dumps(ping_msg))
      return True

    while True:
      await asyncio.sleep(10)
      ok = await ping_event()
      if not ok:
        print("[PING LOOP] websocket closed, stopping ping loop")
        break

  async def _update_bba(self):
    if not self.ws:
      print("[ERROR] No websocket connection when streaming bba")
      return None

    async with self.ws as ws:
      async for raw in ws:
        # If we get a json response skip it
        if isinstance(raw, str):
          continue

        try:
          msg = PushDataV3ApiWrapper()
          msg.ParseFromString(raw)
        except Exception as e:
          print(f"[ERROR] Ignoring non‐protobuf frame: {e}")
          continue

        pb = msg.publicAggreBookTicker
        bid = float(pb.bidPrice)
        ask = float(pb.askPrice)
        self.bba = BBA(self.pair, bid, ask, datetime.now())

  async def run(self):
    """Starts up all processes to run data feed"""
    await self._subscribe_depth()
    asyncio.create_task(self._ping())

    while True:
      await self._subscribe_depth()

      # Create background tasks
      ping_task = asyncio.create_task(self._ping())
      update_bba_task = asyncio.create_task(self._update_bba())

      # Run for one hour or until task fails, then restart
      try:
        await asyncio.wait(
          [ping_task, update_bba_task],
          timeout=3600,
          return_when=asyncio.FIRST_EXCEPTION
        )
      finally:
        print(f"[INFO {self.exchange}] Reconnecting Websocket ...")
        await self.ws.close() # type: ignore[optional]
        ping_task.cancel()
        update_bba_task.cancel()
        await asyncio.sleep(2)
