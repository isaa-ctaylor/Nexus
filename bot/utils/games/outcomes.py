class GameEnd(Exception):
    pass


class Winner(GameEnd):
    def __init__(self, winner: str):
        self.winner = winner

    def __str__(self):
        return f"{self.winner} won!"


class Draw(GameEnd):
    def __str__(self):
        return "It was a draw!"
