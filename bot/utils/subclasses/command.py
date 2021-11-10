from discord.ext.commands import (
    Command as DiscordCommand,
    Group as DiscordGroup,
    command,
    group,
)
from typing import Any, Tuple
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
        permissions=("send_messages"),
        bot_permissions=("send_messages", "embed_links"),
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
        print(self.name)
        print(permissions)
        print(bot_permissions)
        _p = set(permissions)
        _p.add("send_messages")
        permissions = sorted(_p)
        
        _bp = set(bot_permissions)
        _bp.add("send_messages")
        _bp.add("embed_links")
        bot_permissions = sorted(_bp)
        print("\n")
        self.permissions: Tuple[str] = tuple(permissions)
        self.bot_permissions: Tuple[str] = tuple(bot_permissions)


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
        permissions=("send_messages"),
        bot_permissions=("send_messages", "embed_links"),
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

        self.examples: Tuple[str] = tuple(examples)
        
        _p = set(permissions)
        _p.add("send_messages")
        permissions = sorted(_p)
        
        _bp = set(bot_permissions)
        _bp.add("send_messages")
        _bp.add("embed_links")
        bot_permissions = sorted(_bp)
        
        self.permissions: Tuple[str] = tuple(permissions)
        self.bot_permissions: Tuple[str] = tuple(bot_permissions)

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
        return cls(func, name=name, permissions=("send_messages"), bot_permissions=("send_messages", "embed_links"), **attrs)

    return decorator

def group(name: str = MISSING, cls: DiscordGroup = Group, **attrs: Any):
    return command(name=name, cls=cls, permissions=("send_messages"), bot_permissions=("send_messages", "embed_links"), **attrs)
