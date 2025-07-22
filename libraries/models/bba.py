from dataclasses import dataclass
from datetime import datetime

@dataclass
class BBA:
  ts: datetime
  market: str
  best_bid_price: float
  best_bid_size: float
  best_ask_price: float
  best_ask_size: float
