from abc import ABC, abstractmethod
from typing import Optional, List
from websockets.asyncio.client import ClientConnection

from libraries.models.bba import BBA
from libraries.models.trade import Trade

class BaseDataFeed(ABC):
  exchange: str
  pair: str
  ws_url: str
  ws: Optional[ClientConnection]
  bba: Optional[BBA]
  trades: Optional[List[Trade]]

  @abstractmethod
  async def run(self):
    """Starts up all processes to run data feed"""
    pass

  @abstractmethod
  async def _ping(self):
    """Creates loop that sends ping to WebSocket. Return True if response sent back."""
    pass

  def get_best_bid(self):
    if not self.bba:
      print(f"[{self.exchange} {self.pair} ERROR] No BBA to return")
      return

    return self.bba.bid
