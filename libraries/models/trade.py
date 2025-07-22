from datetime import datetime
from dataclasses import dataclass
from libraries.models.side import Side

@dataclass
class Trade:
  ts: datetime
  market: str
  taker_side: Side
  price: float
  amount: float
