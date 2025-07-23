from dataclasses import dataclass
from datetime import datetime
from typing import List, Tuple

@dataclass
class Orderbook:
    ts: datetime
    market: str
    bids: List[Tuple[float, float]]  # (price, size)
    asks: List[Tuple[float, float]]
