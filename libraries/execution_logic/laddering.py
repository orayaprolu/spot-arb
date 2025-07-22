from typing import List, Tuple

def make_buy_ladder(
  best_bid: float,
  total_size: float,
  num_rungs: int = 3,
  spread_width: float = 0.005,
  taper_ratio: float = 1.0,
) -> List[Tuple[float, float]]:
  """
  Build a buy-ladder under best_bid.

  - best_bid: current best bid price
  - total_size: total quantity you want to buy
  - num_rungs: number of limit orders
  - spread_width: total % below best_bid to reach (e.g. 0.005 for 0.5%)
  - taper_ratio: geometric ratio for size taper (1.0 = equal sizes,
                  0.5 = halves each rung, etc.)
  Returns list of (limit_price, size) tuples, rung0 is at best_bid.
  """
  # compute prices linearly spaced from best_bid down to best_bid * (1 - spread_width)
  prices = [
    best_bid * (1 - spread_width * i / (num_rungs - 1))
    for i in range(num_rungs)
  ]

  # compute geometric sizes if taper_ratio != 1.0, else equal
  if taper_ratio == 1.0:
    sizes = [total_size / num_rungs] * num_rungs
  else:
    # sum of a geometric series: a * (1 - r^n) / (1 - r) = total_size
    r = taper_ratio
    a = total_size * (1 - r) / (1 - r**num_rungs)
    sizes = [a * (r**i) for i in range(num_rungs)]

  return list(zip(prices, sizes))
