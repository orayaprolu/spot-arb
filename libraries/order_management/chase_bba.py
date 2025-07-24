import asyncio

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.data_ingestion.mexc_data_feed import MexcDataFeed
from libraries.exchange_clients.coinex_exchange_client import CoinexExchangeClient
from libraries.models.bba import BBA
from libraries.models.coinex_order_data import CoinexOrderData
from libraries.models.coinex_place_order_request import CoinexPlaceOrderRequest
from libraries.models.coinex_cancel_all_orders_request import CoinexCancelAllOrdersRequest

from utils.difference_in_bps import difference_in_bps

class ChaseBBA():
  def __init__(
    self,
    pair: str,
    minimum_bps_threshold: float,
    coinex_feed: CoinexDataFeed,
    mexc_feed: MexcDataFeed,
    coinex_exchange_client: CoinexExchangeClient,

  ):
    self.pair = pair.replace('-', '')
    self.minimum_bps_threshold = minimum_bps_threshold

    self.coinex_feed: CoinexDataFeed = coinex_feed
    self.mexc_feed: MexcDataFeed = mexc_feed

    self.coinex_exchange_client: CoinexExchangeClient = coinex_exchange_client

    self.coinex_bba: BBA | None = None
    self.mexc_bba: BBA | None = None

    self.visible_order: CoinexOrderData | None = None
    self.hidden_order: CoinexOrderData | None = None
    self.prev_coinex_bba: BBA | None = None

  async def consume_coinex_bba(self, queue):
    while True:
      self.coinex_bba = await queue.get()

  async def consume_mexc_bba(self):
    while True:
      await asyncio.sleep(1)
      self.mexc_bba = self.mexc_feed.bba

  def place_orders(self, amount_usd: float, hidden_to_visible_ratio: float = 20.0, visible_only: bool = False, hidden_only: bool = False):
    if not self.coinex_bba:
      print("No coinex bba, can't place order")
      return

    p0 = self.coinex_bba.best_bid_price

    # visible + hidden = amount_usd
    # hidden = hidden_to_visible_ratio × visible
    # → visible * (1 + hidden_to_visible_ratio) = amount_usd
    visible_usd = amount_usd / (1 + hidden_to_visible_ratio)
    hidden_usd  = amount_usd - visible_usd

    amount_pair_visible = visible_usd / p0
    amount_pair_hidden  = hidden_usd  / p0

    if not hidden_only:
      self._place_visible_order(p0, amount_pair_visible)

    if not visible_only:
      self._place_hidden_order(p0, amount_pair_hidden)

  def _place_visible_order(self, p0: float, amount_pair: float):
    visible_order_request = CoinexPlaceOrderRequest(
      market = self.pair,
      side = "buy",
      amount = str(amount_pair),
      price = str(p0),
    )

    try:
      visible_order = self.coinex_exchange_client.place_order(visible_order_request)
      self.visible_order = visible_order.data
    except Exception as e:
      print(f"[ERROR] Failed to place visible order: {e}")
      self.visible_order = None

  def _place_hidden_order(self, p0: float, amount_pair: float):
    hidden_order_request = CoinexPlaceOrderRequest(
      market = self.pair,
      side = "buy",
      amount = str(amount_pair),
      price = str(p0),
      is_hide = True
    )

    try:
      hidden_order = self.coinex_exchange_client.place_order(hidden_order_request)
      self.hidden_order = hidden_order.data
    except Exception as e:
      print(f"[ERROR] Failed to place hidden order: {e}")
      self.hidden_order = None

  def cancel_orders(self):
    self.coinex_exchange_client.cancel_all_orders(CoinexCancelAllOrdersRequest(market=self.pair))
    self.visible_order = None
    self.hidden_order = None

  async def run(self, limit_amount_usd: float):
    asyncio.create_task(self.consume_coinex_bba(self.coinex_feed.bba_queue))
    asyncio.create_task(self.consume_mexc_bba())

    while True:
      await asyncio.sleep(1)

      if not self.coinex_bba or not self.mexc_bba:
        print("Waiting for BBA's to populate")
        continue

      coinex_bid = self.coinex_bba.best_bid_price
      mexc_bid =  self.mexc_bba.best_bid_price
      bps = difference_in_bps(coinex_bid, mexc_bid)

      # If the Bps spread falls below 30, we just want to cancel and not replace order
      # TODO: Change this to a more nuaced "leave in market at 30 bps" later
      print("BPS ARB:", bps)
      if bps < self.minimum_bps_threshold:
        print(f"Arb less than {self.minimum_bps_threshold} bps, canceling")
        self.cancel_orders()
        continue

      if not self.visible_order and not self.hidden_order:
        print("Currently no orders, creating one now")
        self.place_orders(limit_amount_usd)
        continue

      # When do we want to replace order:
      # 1) The BBA changes
      if (
        (self.visible_order and float(self.visible_order.price) != coinex_bid)
        or
        (self.hidden_order and float(self.hidden_order.price) != coinex_bid)
      ):
        print("BBA Changed, moving orders")
        self.cancel_orders()
        self.place_orders(limit_amount_usd)
        continue

      #TODO: FIX THIS IT CURRENTLY CAN'T TELL THIS CAUSE WE NEVER QUERY THE API FOR IT (Actually we might not need this since bba changes)
      # 2) Order is fully filled
      if self.visible_order and self.visible_order.unfilled_amount == 0:
        print("Visible order fully filled, replacing it")
        self.place_orders(limit_amount_usd, visible_only = True)
        continue
      if self.hidden_order and self.hidden_order.unfilled_amount == 0:
        print("Hidden order fully filled, replacing it")
        self.place_orders(limit_amount_usd, hidden_only = True)
        continue

      # Otherwise just leave the order alone

  # Calculate where we should place order: if bps are above 30 just put at bba, if below 30 but it at 30
  #   We also want to have our order on three levels laddering down which is why we need the orderbook data
  # If current orders are at this level then skip
  # otherwise cancel stale orders and replace them with correct levels
  #
  # Should constantly be checking every second or so to see if anything was filled, if so immediately be sure to create new orders
  # at calculated limit prices



# Visible order is 1/20 th of hidden order
