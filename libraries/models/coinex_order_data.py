from dataclasses import dataclass

@dataclass
class CoinexOrderData:
    order_id: str
    market: str
    market_type: str
    ccy: str
    side: str
    type: str
    amount: str
    price: str
    unfilled_amount: str
    filled_amount: str
    filled_value: str
    client_id: str
    base_fee: str
    quote_fee: str
    discount_fee: str
    maker_fee_rate: str
    taker_fee_rate: str
    last_fill_amount: str
    last_fill_price: str
    created_at: int
    updated_at: int
