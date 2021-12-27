from typing import Iterable, Union
from .config import *
from .helpers import *
from time import time
import functools
import asyncio


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
        self.elapsed = (self._end - self._start) * 1000


def naturallist(iterable: Iterable, delimiter: str = ", "):
    if len(iterable) == 1:
        return str(iterable[0])

    iterable = [str(i) for i in iterable]

    return delimiter.join(iterable[:-1]) + f" and {iterable[-1]}"

def executor(sync_function):
    @functools.wraps(sync_function)
    async def sync_wrapper(*args, **kwargs):
        """
        Asynchronous function that wraps a sync function with an executor.
        """

        loop = asyncio.get_event_loop()
        internal_function = functools.partial(sync_function, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return sync_wrapper

def hyperlink(text, uri):
    if uri is None:
        return text
    return f"[{text}]({uri})"

def codeblock(text, language=""):
    return f"```{language}\n{text}```"
