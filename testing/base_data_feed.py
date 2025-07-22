from libraries.models.bba import BBA
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from websockets.asyncio.client import ClientConnection
import asyncio

class BaseDataFeed(ABC):
  ws_url: str
  ws: ClientConnection | None
  pair: str
  bba: Optional[BBA]

  @abstractmethod
  async def _ping(self):
    """Creates loop that sends ping to WebSocket. Return True if response sent back."""
    pass

  # async def get_latest_bba(self, symbol: str) -> BBA | None:
  #   """Get the most recent BBA for a symbol."""
  #   return self._bba
