from dataclasses import dataclass
from typing import Optional

@dataclass
class CoinexCancelAllOrdersRequest:
    market: str
    market_type: str = "SPOT"
    side: Optional[str] = None  # Optional (can be "buy" or "sell")
