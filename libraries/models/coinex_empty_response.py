from dataclasses import dataclass

@dataclass
class CoinexEmptyResponse:
    code: int
    data: dict  # always empty
    message: str
