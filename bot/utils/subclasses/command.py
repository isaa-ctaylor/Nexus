from discord.ext.commands import (
    Command as DiscordCommand,
    Group as DiscordGroup,
    command,
    group,
)
from typing import Any
from discord.utils import MISSING


class Command(DiscordCommand):
    def __init__(
        self,
        callback,
        name,
        *,
        aliases=(),
        brief=None,
        description="",
        usage=None,
        hidden=False,
        examples=(),
        **kwargs
    ):
        super().__init__(
            callback,
            name=name,
            aliases=aliases,
            brief=brief,
            description=description,
            usage=usage,
            hidden=hidden,
            **kwargs
        )

        self.examples = tuple(examples)


class Group(DiscordGroup):
    def __init__(
        self,
        callback,
        name,
        *,
        aliases=(),
        brief=None,
        description="",
        usage=None,
        hidden=False,
        examples=(),
        **kwargs
    ):
        super().__init__(
            callback,
            name=name,
            aliases=aliases,
            brief=brief,
            description=description,
            usage=usage,
            hidden=hidden,
            **kwargs
        )

        self.examples = tuple(examples)

    def command(self, *args, **kwargs):
        def wrapper(func):
            kwargs.setdefault("parent", self)
            result = command(cls=Command, *args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapper

    def group(self, *args, **kwargs):
        def wrapper(func):
            kwargs.setdefault("parent", self)
            result = group(cls=Group, *args, **kwargs)(func)
            self.add_command(result)
            return result

        return wrapper

def command(name: str = MISSING, cls: object = Command, **attrs: Any):
    def decorator(func):
        if isinstance(func, Command):
            raise TypeError('Callback is already a command.')
        return cls(func, name=name, **attrs)

    return decorator

def group(name: str = MISSING, cls: DiscordGroup = Group, **attrs: Any):
    return command(name=name, cls=cls, **attrs)
