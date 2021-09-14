from discord.ext.commands import Context
from discord import Embed
from discord.message import Message
from ..helpers import Paginator
from copy import copy
from discord.errors import Forbidden


class NexusContext(Context):
    async def embed(self, **kwargs):
        kwargs["colour"] = kwargs.pop("colour", self.bot.config.data.colours.neutral)

        destination = kwargs.pop("destination", self)
        paginate = kwargs.pop("paginate", True)

        if paginate:
            return await self.paginate(Embed(**kwargs), destination=destination)

        return await destination.send(embed=Embed(**kwargs))

    async def defer(self) -> None:
        if self.interaction:
            await self.interaction.response.defer()

    async def paginate(self, *items, **kwargs) -> None:
        if self.interaction:
            await self.defer()

        destination = kwargs.pop("destination", self)

        if len(items) == 1 and isinstance(items[0], (list, tuple)):
            items = [item for item in items[0]]

        p = Paginator(self)

        return await p.send(items, destination=destination)

    async def copy_with(self, *, author=None, channel=None, **kwargs):
        _msg: Message = copy(self.message)
        _msg._update(kwargs)

        if author is not None:
            _msg.author = author
        if channel is not None:
            _msg.channel = channel

        _msg.content = kwargs["content"]

        return await self.bot.get_context(_msg, cls=type(self))

    async def error(self, message: str):
        try:
            await self.paginate(
                Embed(
                    title="Error!",
                    description=f"```\n{message}```",
                    colour=self.bot.config.data.colours.bad,
                )
            )
        except Forbidden:
            await self.paginate(message)
