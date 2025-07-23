import time
import hmac
import hashlib
import requests
import json
from urllib.parse import urlencode

from libraries.models.coinex_place_order_response import CoinexPlaceOrderResponse
from libraries.models.coinex_order_data import CoinexOrderData
from libraries.models.coinex_place_order_request import CoinexPlaceOrderRequest
from libraries.models.coinex_cancel_all_orders_request import CoinexCancelAllOrdersRequest
from libraries.models.coinex_empty_response import CoinexEmptyResponse
from libraries.models.coinex_cancel_order_request import CoinexCancelOrderRequest
from libraries.models.coinex_cancel_order_response import CoinexCancelOrderResponse

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

  def place_order(self, req: CoinexPlaceOrderRequest) -> CoinexPlaceOrderResponse:
    body = {
      "market": req.market.replace("-", ""),
      "market_type": req.market_type,
      "side": req.side,
      "type": req.type,
      "amount": req.amount,
      "price": req.price,
    }

    # Optional fields
    if req.ccy is not None:
      body["ccy"] = req.ccy
    if req.client_id is not None:
      body["client_id"] = req.client_id
    if req.is_hide:
      body["is_hide"] = True  # type: ignore
    if req.stp_mode is not None:
      body["stp_mode"] = req.stp_mode

    resp_dict = self._request("POSTa", "/v2/spot/order", body=body)
    return CoinexPlaceOrderResponse(
      code=resp_dict["code"],
      data=CoinexOrderData(**resp_dict["data"]),
      message=resp_dict["message"]
    )

  def cancel_all_orders(self, req: CoinexCancelAllOrdersRequest) -> CoinexEmptyResponse:
    body = {
      "market": req.market.replace("-", ""),
      "market_type": req.market_type,
    }
    if req.side:
      body["side"] = req.side

    resp = self._request("POST", "/v2/spot/cancel-all-order", body=body)
    return CoinexEmptyResponse(**resp)

  def cancel_order(self, req: CoinexCancelOrderRequest) -> CoinexCancelOrderResponse:
    body = {
      "market": req.market.replace("-", ""),
      "market_type": req.market_type,
      "order_id": req.order_id
    }

    resp = self._request("POST", "/v2/spot/cancel-order", body=body)
    return CoinexCancelOrderResponse(
      code=resp["code"],
      message=resp["message"],
      data=CoinexOrderData(**resp["data"])
    )
