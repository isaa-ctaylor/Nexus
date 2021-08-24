from functools import partial
from typing import Callable
from .config import *
from .helpers import *


def codeblocksafe(string: Union[str, Any]):
    return str(string).replace("`", "\u200b`\u200b")


def execute(func: Callable):
    async def inner(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, partial(func, *args, **kwargs)
        )

    return inner
