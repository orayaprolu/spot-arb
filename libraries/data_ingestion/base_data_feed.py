from abc import ABC, abstractmethod
from typing import Optional, List
from websockets.asyncio.client import ClientConnection
import asyncio

from libraries.models.bba import BBA
from libraries.models.trade import Trade

class BaseDataFeed(ABC):
  exchange: str
  pair: str
  ws_url: str
  ws: Optional[ClientConnection]
  bba_queue: asyncio.Queue[BBA]
  trade_queue: asyncio.Queue[Trade]

  @abstractmethod
  async def run(self):
    """Starts up all processes to run data feed"""
    pass

  @abstractmethod
  async def _ping(self):
    """Creates loop that sends ping to WebSocket. Return True if response sent back."""
    pass
