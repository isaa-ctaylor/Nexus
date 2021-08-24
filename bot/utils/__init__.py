from functools import wraps, partial
from typing import Callable
from .config import *
from .helpers import *


def codeblocksafe(string: Union[str, Any]):
    return str(string).replace("`", "\u200b`\u200b")
