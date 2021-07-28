from discord.ext.commands import Context
from discord import Embed
from ..helpers import Paginator


class NexusContext(Context):
    async def embed(self, **kwargs):
        kwargs["colour"] = kwargs.pop(
            "colour", self.bot.config.data.colours.neutral
        )

        destination = kwargs.pop("destination", self)

        return await destination.send(embed=Embed(**kwargs))

    async def paginate(self, *items):
        if len(items) == 1 and isinstance(items[0], (list, tuple)):
            items = [item for item in items[0]]

        p = Paginator(self)

        return await p.send(items)
