from discord.ext.commands import Command as DiscordCommand


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
