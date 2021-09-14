from typing import Union
from .config import *
from .helpers import *
from time import time
import textwrap
from .subclasses.command import Group, Command


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

def cmdtree(commands: List[Union[Command, Group]]):
    lines = []

    for number, command in enumerate(commands, start=1):
        prefix = "└── " if number == len(commands) else "├── "
        lines.append(f"{prefix}{command.name}")

        if isinstance(command, Group):
            indent = "\t" if number == len(commands) else "|\t"
            subcommands = textwrap.indent(cmdtree(command.commands), prefix=indent)
            lines.append(subcommands)

    return "\n".join(lines)
