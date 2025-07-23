from dataclasses import dataclass

@dataclass
class CoinexCancelOrderRequest:
    market: str
    order_id: int
    market_type: str = "SPOT"
