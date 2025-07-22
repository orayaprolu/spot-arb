def difference_in_bps(num1: float, num2: float) -> float:
  """
  Return (num2 - num1) / num1 in basis points.
  """
  if num1 == 0:
      raise ValueError("num1 must be non-zero")
  return (num2 - num1) / num1 * 10_000
