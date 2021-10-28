from typing import Any


class Player:
    def __init__(self, symbol: str, identifier: Any = None, *, ai: bool = False):
        self.symbol = symbol
        self.identifier = identifier or symbol
        self.ai = ai

    def __str__(self):
        return self.symbol
