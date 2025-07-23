# FIX THESE CONSUMES + ORDERBOOK ONE TO WORK FOR THIS ORDER MANAGER
async def consume_bba(queue):
  while True:
    bba = await queue.get()
    print(f"[BBA] {bba.ts} | {bba.market} | bid: {bba.best_bid_price:.5f} x {bba.best_bid_size:.2f} | ask: {bba.best_ask_price:.5f} x {bba.best_ask_size:.2f}")

async def consume_trades(queue):
  while True:
    trade = await queue.get()
    print(f"[TRADE] {trade.ts} | {trade.market} | {trade.taker_side.name} | {trade.amount:.2f} @ {trade.price:.5f}")


class ChaseBbaOrderManager():
  def __init__(self) -> None:
    pass

  async def run(self):



  # Calculate where we should place order: if bps are above 30 just put at bba, if below 30 but it at 30
  #   We also want to have 25% of our order at the top level and 75% of our order at the level directly below which is why we need the orderbook data
  # Check bps to see if above 30 (or whatever minimum)
