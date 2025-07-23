from dataclasses import dataclass
from libraries.models.coinex_order_data import CoinexOrderData

@dataclass
class CoinexCancelOrderResponse:
    code: int
    data: CoinexOrderData
    message: str
