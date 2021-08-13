from discord.ext.commands import (
    Command as DiscordCommand,
    Group as DiscordGroup,
    command,
    group,
)


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
