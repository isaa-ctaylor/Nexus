from functools import wraps, partial
from typing import Union
from .config import *
from .helpers import *
from time import sleep, time


def codeblocksafe(string: Union[str, Any]):
    return str(string).replace("`", "\u200b`\u200b")


class Timer:
    _start = None
    _end = None
    elapsed = None

    def __enter__(self):
        self._start = time()
        return self

    def __exit__(self, *_):
        self.end()

    def end(self):
        self._end = time()
        self.elapsed = self._end - self._start
