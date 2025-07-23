from dataclasses import dataclass
from libraries.models.coinex_order_data import CoinexOrderData

@dataclass
class CoinexPlaceOrderResponse:
    code: int
    data: CoinexOrderData
    message: str
