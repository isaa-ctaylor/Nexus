import random
import asyncio
import typing
from collections import deque
from enum import Enum
import contextlib


class Loop(Enum):
    OFF = 1
    ALL = 2
    ONE = 3


class AsyncLoopShuffleQueue:
    def __init__(self, items: typing.Optional[typing.List[typing.Any]] = []) -> None:
        self._original = deque(items)
        self._queue = deque(items)
        self._up_next = asyncio.Queue()

        for i in items:
            self._up_next.put_nowait(i)

        self._current = None

        self._history = deque()

        self._shuffled = False
        self._loop: Loop = Loop.OFF

    def put(self, item: typing.Any) -> None:
        self._original.append(item)
        self._queue.append(item)
        self._up_next.put_nowait(item)

    def putleft(self, item: typing.Any) -> None:
        self._original.appendleft(item)
        self._queue.appendleft(item)
        self._up_next._queue.appendleft(item)

    async def get(self, *, force: bool = True) -> typing.Optional[typing.Any]:
        ret = None

        if self._loop is Loop.ONE and not force:
            ret = self._current
        else:
            if self._up_next.empty():
                if self._loop.ALL:
                    self._up_next = asyncio.Queue()
                    for i in list(self._queue):
                        self._up_next.put_nowait(i)

            ret = await self._up_next.get()

        if self._current is not None and (self._loop is not Loop.ONE):
            self._history.append(self._current)

        self._current = ret

        return ret

    def previous(self) -> typing.Optional[typing.Any]:
        ret = None

        add_to_queue = False

        try:
            ret = self._history.pop()
            add_to_queue = True
        except IndexError:
            ret = None

        if add_to_queue:
            self._up_next._queue.appendleft(self._current)

        return ret

    def loop(self) -> Loop:
        if self._loop is Loop.OFF:
            self._loop = Loop.ALL
        else:
            if self._loop is Loop.ALL:
                self._loop = Loop.ONE
                if self._current in self._original:
                    index = self._queue.index(self._current)
                else:
                    index = 0

                self._history = deque(list(self._queue)[:index])
            else:
                self._loop = Loop.OFF

        return self._loop

    def shuffle(self) -> bool:
        if self._shuffled:
            # Find current song index in self._original
            # Put all before current in history (reversed)
            # Put all after current in queue (in order)
            if self._current in self._original:
                index = self._original.index(self._current) + 1
            else:
                index = 0

            self._queue = self._original.copy()
            self._up_next = asyncio.Queue()
            for i in list(self._queue)[index:]:
                self._up_next.put_nowait(i)

            self._shuffled = False

        else:
            queue = list(self._queue)
            with contextlib.suppress(ValueError):
                current = queue.pop(queue.index(self._current))
            random.shuffle(queue)
            self._up_next = asyncio.Queue()
            for i in queue:
                self._up_next.put_nowait(i)

            queue.insert(0, current)
            self._queue = deque(queue)

            self._shuffled = True

        return self._shuffled
