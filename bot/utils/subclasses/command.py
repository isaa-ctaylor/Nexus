from inspect import getsource
import re
from discord.ext.commands import (
    Command as DiscordCommand,
    Group as DiscordGroup,
    command,
    group,
)
from typing import Any, Tuple
from discord.utils import MISSING


PERM_PATTERNS = {
    "User channel permissions": r"@has_permissions\((?P<perms>[a-zA-Z_=, \n]+)\)",
    "User guild permissions": r"@has_guild_permissions\((?P<perms>[a-zA-Z_=, \n]+)\)",
    "Bot channel permissions": r"@bot_has_permissions\((?P<perms>[a-zA-Z_=, \n]+)\)",
    "Bot guild permissions": r"@bot_has_guild_permissions\((?P<perms>[a-zA-Z_=, \n]+)\)",
}


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

        self.permissions = {}

        source = getsource(self.callback)

        for ptype, pattern in PERM_PATTERNS.items():
            _m = re.match(pattern, source)

            perms = set(
                _m.group("perms")
                .replace(" ", "")
                .replace("\n", "")
                .replace("=True", "")
                .split(",")
                if _m is not None
                else []
            )

            perms.add("send_messages")
            if "bot" in ptype.lower():
                perms.add("embed_links")

            self.permissions[ptype] = sorted(perms)


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

        self.permissions = {}

        source = getsource(self.callback)

        for ptype, pattern in PERM_PATTERNS.items():
            _m = re.match(pattern, source)

            perms = set(
                _m.group("perms")
                .replace(" ", "")
                .replace("\n", "")
                .replace("=True", "")
                .split(",")
                if _m is not None
                else []
            )

            perms.add("send_messages")
            if "bot" in ptype.lower():
                perms.add("embed_links")

            self.permissions[ptype] = sorted(perms)

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
            raise TypeError("Callback is already a command.")
        return cls(func, name=name, **attrs)

    return decorator


def group(name: str = MISSING, cls: DiscordGroup = Group, **attrs: Any):
    return command(name=name, cls=cls, **attrs)
