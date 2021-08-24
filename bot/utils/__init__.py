from functools import wraps, partial
from typing import Callable
from .config import *
from .helpers import *


def codeblocksafe(string: Union[str, Any]):
    return str(string).replace("`", "\u200b`\u200b")


def execute(func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        internal_function = partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, internal_function)

    return wrapper
