import time
import hmac
import hashlib
import requests
import json
from urllib.parse import urlencode

COINEX_HTTP = 'https://api.coinex.com'


class CoinexExchangeClient:

  def __init__(self, access_id: str, secret_key: str):
    self.http_url = COINEX_HTTP
    self.access_id = access_id
    self.secret_key = secret_key

  def _request(
    self,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
  ) -> dict:
    """
    Send a signed request to CoinEx.
    method: "GET", "POST", etc.
    path: API path, e.g. "/v2/account/info"
    params: query parameters to include in URL
    body: JSON‐serializable body for POST/PUT
    """
    ts = str(int(time.time() * 1000))

    # build query string for signing & URL
    qs = ""
    if params:
      qs = "?" + urlencode(params)

    body_str = json.dumps(body, separators=(",", ":")) if body else ""
    to_sign = method.upper() + path + qs + body_str + ts

    signature = (
      hmac.new(
        self.secret_key.encode("latin-1"),
        msg=to_sign.encode("latin-1"),
        digestmod=hashlib.sha256,
      )
      .hexdigest()
      .lower()
    )

    headers = {
      "X-COINEX-KEY": self.access_id,
      "X-COINEX-SIGN": signature,
      "X-COINEX-TIMESTAMP": ts,
      "Content-Type": "application/json",
    }

    url = self.http_url + path + qs
    resp = requests.request(method, url, headers=headers, data=body_str)
    resp.raise_for_status()
    return resp.json()

  def get_account_info(self) -> dict:
    '''Get account information'''
    return self._request("GET", "/v2/account/info")

  def place_order(
    self,
    pair: str,
    side: str,
    amount: float,
    price: float,
    ccy: str | None = None,
    client_id: str | None = None,
    is_hide: bool = False,
    stp_mode: str | None = None,
  ) -> dict:
    """
    Place a spot order.

    Required:
      pair      – e.g. "BTC-USDT"
      side        – "buy" or "sell"
      order_type  – "limit" or "market"
      amount      – order quantity as string
      price       – limit price (required for limit orders)

    Optional:
      ccy         – for market orders, which currency ("BTC" or "USDT")
      client_id   – your own client‐side ID
      is_hide     – hide in public depth (True/False)
      stp_mode    – self‐trade protection: "ct", "cm", or "both"
    """
    market = pair.replace('-', '')
    body: dict = {
      "market":      market,
      "market_type": "SPOT",
      "side":        side,
      "type":        "limit",
      "amount":      str(amount),
      "price":       str(price)
    }

    if price is not None:
      body["price"] = price
    if ccy is not None:
      body["ccy"] = ccy
    if client_id is not None:
      body["client_id"] = client_id
    if is_hide:
      body["is_hide"] = True
    if stp_mode is not None:
      body["stp_mode"] = stp_mode

    # POST to /v2/spot/order
    return self._request("POST", "/v2/spot/order", body=body)

  def cancel_all_orders(self, pair: str):
    '''Cancels all orders of a specfic pair'''
    body = {
      "market": pair.replace("-", ""),
      "market_type": "SPOT"
    }
    return self._request("POST", "/v2/spot/cancel-all-order", body=body)

  def cancel_order(self, pair: str, order_id: str):
    body = {
      "market": pair.replace("-", ""),
      "market_type": "SPOT",
      "order_id": int(order_id)
    }
    return self._request("POST", "/v2/spot/cancel-order", body=body)
