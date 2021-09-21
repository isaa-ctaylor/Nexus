from typing import Any

from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import CommandError
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command, group
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext


class InvalidPlayer(CommandError):
    def __init__(self, player: str):
        self.player = player

    def __str__(self):
        return f"{self.player} is not a valid player!"


class Player(Converter):
    async def convert(self, ctx: NexusContext, query: Any):
        async with ctx.bot.session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{query}"
        ) as resp:
            if resp.status == 200:
                return await resp.json()

        async with ctx.bot.session.get(
            "https://api.mojang.com/profiles/minecraft", data=[str(query)]
        ) as resp:
            d = await resp.json()

            if d:
                return {"id": d[0]["id"], "name": d[0]["name"]}

        raise InvalidPlayer(query)


class Minecraft(Cog):
    """
    Commands related to Minecraft
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

    @group(name="minecraft", aliases=["mc"], invoke_without_command=True)
    async def _minecraft(self, ctx: NexusContext):
        """
        Minecraft commands.

        Functionality is within the subcommands.
        """
        if not ctx.invoked_subcommand:
            return await ctx.send_help(ctx.command)

    @_minecraft.command(name="player")
    async def _minecraft_player(self, ctx: NexusContext, player: Player):
        """
        Get minecraft player info.
        """
        await ctx.send(str(player))

    @_minecraft_player.error
    async def _minecraft_player_error(self, ctx: NexusContext, error: Exception):
        """
        Handles Player converter error
        """
        if isinstance(error, InvalidPlayer):
            return await ctx.error(str(error))

        raise error


def setup(self, bot: Nexus):
    bot.add_cog(Minecraft(bot))
