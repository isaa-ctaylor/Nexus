from typing import Any
from discord.embeds import Embed

from discord.ext.commands.converter import Converter
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command, group
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext

from utils import codeblocksafe


class Player(Converter):
    async def convert(self, ctx: NexusContext, query: Any):
        async with ctx.bot.session.get(
            f"https://api.mojang.com/users/profiles/minecraft/{query}"
        ) as resp:
            if resp.status == 200:
                return await resp.json()

        async with ctx.bot.session.get(
            f"https://api.mojang.com/user/profiles/{query}/names"
        ) as resp:
            if resp.status == 200:
                d = await resp.json()

                if "errorMessage" not in d:
                    return {"id": query, "name": d[-1]["name"]}

        return {"error": f"{codeblocksafe(query)} is not a valid name!"}


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
        if "error" in player:
            return await ctx.error(player["error"])

        embed = Embed(
            title="Minecraft player info", colour=self.bot.config.colours.neutral
        )

        embed.set_thumbnail(
            url=f"https://crafatar.com/renders/body/{player['id']}?overlay"
        )

        embed.add_field(name="Name", value=f'```\n{player["name"]}```')
        embed.add_field(name="UUID", value=f'```\n{player["id"]}```')

        await ctx.paginate(embed)

    @_minecraft.command(name="skin")
    async def _minecraft_skin(self, ctx: NexusContext, player: Player):
        """
        See the skin of the given player
        """
        if "error" in player:
            return await ctx.error(player["error"])

        embed = Embed(
            title=f"{player['name']}'s skin", colour=self.bot.config.colours.neutral
        )

        embed.set_image(url=f"https://crafatar.com/renders/body/{player['id']}?overlay")

        await ctx.paginate(embed)


def setup(bot: Nexus):
    bot.add_cog(Minecraft(bot))
