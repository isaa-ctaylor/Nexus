from itertools import chain, cycle
from typing import Callable, List, Tuple
import re
import numpy
from .player import Player
from .outcomes import Winner, Draw


def pdiag(array: numpy.ndarray):
    h, w = len(array), len(array[0])
    return [
        [array[h - p + q - 1][q] for q in range(max(p - h + 1, 0), min(p + 1, w))]
        for p in range(h + w - 1)
    ]


def ndiag(array: numpy.ndarray):
    h, w = len(array), len(array[0])
    return [
        [array[p - q][q] for q in range(max(p - h + 1, 0), min(p + 1, w))]
        for p in range(h + w - 1)
    ]


class ConnectFour:
    """
    The Connect Four class

    Parameters
    ==========

    rows: int
        The number of rows you want to start your game with
    columns: int
        The number of columns you want to start your game with
    towin: int
        The number of counters in a row you need to win
    placeholder: str
        The "background" character for your game
    players: Tuple[Player]
        The two players. Defaults to 🔴 and 🟡
    """

    def __init__(
        self,
        *,
        rows: int = 6,
        columns: int = 7,
        towin: int = 4,
        placeholder: str = "⬛",
        players: Tuple[Player] = (Player("🔴"), Player("🟡")),
    ):
        self._board: List[List[str]] = [
            [placeholder for _ in range(rows)] for _ in range(columns)
        ]

        self._placeholder = placeholder
        self._towin = towin

        self._players = players
        self._player = cycle(players)

    def render(self, *, func: Callable = zip):
        """
        Render the board

        Returns
        =======

        board: str
            The rendered board
        """
        return "\n".join(" ".join(str(_) for _ in _) for _ in func(*self._board))

    __str__ = render

    def _check_win(self, player: Player):
        _board = self._board.copy()

        def predicate(board: str, player: Player):
            match = re.findall(f"{player.symbol}{'{' + str(self._towin) + '}'}", board)
            if match:
                raise Winner(player.identifier)

        predicate(self.render().replace(" ", ""), player)

        predicate(self.render(func=lambda *_: _).replace(" ", ""), player)

        _ = numpy.array(_board)

        items = [item for item in chain(pdiag(_), ndiag(_)) if len(item) >= self._towin]

        for item in items:
            _ = "".join(str(i) for i in item)

            if player.identifier * self._towin in _:
                raise Winner(player.identifier)

    def place(self, column: int):
        """
        Place a counter on the board

        Parameters
        ==========

        column: int
            The column to place a counter in

        Raises
        ======

        ValueError
            The column you are trying to place in is full
        IndexError
            The requested column does not exist

        Returns
        =======

        board: str
            The rendered board
        """
        if column > len(self._board):
            raise IndexError(f"Column {column} does not exist!")

        player = next(self._player)

        c = self._board[column - 1]

        for index, item in enumerate(c):
            if item != self._placeholder:
                if index < 1:
                    next(self._player)
                    raise ValueError("That row is full!")

                c[index - 1] = player
                break

            if index == len(c) - 1:
                c[len(c) - 1] = player

        self._board[column - 1] = c

        self._check_win(player)

        if all(i != self._placeholder for i in chain(*self._board)):
            raise Draw

        return self.render()
