from typing import Optional, Tuple
from player import Player
from outcomes import Winner, Draw
from itertools import cycle
from xo.ai import evaluate
from xo.board import Board
import random


class TicTacToe:
    def __init__(
        self,
        *,
        placeholder: str = "⬛",
        players: Tuple[Player] = (Player("❌"), Player("⭕")),
    ):
        self._board = [[placeholder for _ in range(3)] for _ in range(3)]

        self._placeholder = placeholder

        players[0]._ttt_identifier = "x"
        players[1]._ttt_identifier = "o"

        self._players = players
        self._player = cycle(players)

    def render(self):
        return "\n".join(" ".join(str(_) for _ in _) for _ in self._board)

    __str__ = render

    def place(self, position: Optional[int] = None):
        """
        Place the next counter
        """
        if position:
            posmap = {
                1: (1, 1),
                2: (1, 2),
                3: (1, 3),
                4: (2, 1),
                5: (2, 2),
                6: (2, 3),
                7: (3, 1),
                8: (3, 2),
                9: (3, 3),
            }

            x, y = posmap[position]
        
            if place := self._board[x - 1][y - 1] != self._placeholder:
                raise KeyError(f"{place} has already played there!")

        player = next(self._player)

        if player.ai:
            result = evaluate(
                Board.fromstring(
                    "".join(
                        "".join(
                            "." if _ == self._placeholder else _._ttt_identifier
                            for _ in _
                        )
                        for _ in self._board
                    )
                ),
                player._ttt_identifier,
            )

            x, y = random.choice(result.positions)

        self._board[x - 1][y - 1] = player

        self._check_win(player)

        return self.render()

    def _check_win(self, player: Player):
        board = self._board.copy()

        for _ in [board, list(zip(*board))]:
            for row in _:
                if all(_ == row[0] for _ in row) and self._placeholder not in row:
                    raise Winner(player.identifier)

        diagonals = ([self._board[2][2], self._board[1][1], self._board[0][0]],)
        [
            self._board[0][2],
            self._board[1][1],
            self._board[2][0],
        ]

        for _ in diagonals:
            if all(__ == _[0] for __ in _) and self._placeholder not in _:
                raise Winner(player.identifier)
