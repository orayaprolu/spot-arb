from dataclasses import dataclass
from typing import Optional

@dataclass
class CoinexPlaceOrderRequest:
    market: str
    market_type: str = "SPOT"
    side: str = "buy"         # or "sell"
    type: str = "limit"
    amount: str = "0"
    price: str = "0"
    ccy: Optional[str] = None
    client_id: Optional[str] = None
    is_hide: Optional[bool] = False
    stp_mode: Optional[str] = None
