from typing import Any, Optional
from discord.embeds import Embed
from discord.ext.commands.converter import Converter
from discord.ext.commands.core import command
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.context import NexusContext
from utils import codeblocksafe


class Prefix(Converter):
    async def convert(self, ctx: NexusContext, argument: Any):
        argument = str(argument)
        if argument.startswith('"') and argument.endswith('"'):
            return argument[1:-1]
        return argument


class Settings(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    @command(name="prefix", cls=Command)
    async def _prefix(self, ctx: NexusContext, prefix: Optional[Prefix] = None):
        if not prefix:
            prefix = self.bot.prefixes.get(ctx.guild.id, ["Nxs"])[0]

            return await ctx.paginate(
                Embed(
                    title="Prefix",
                    description=f"```\nThe prefix for {codeblocksafe(ctx.guild.name)} is {codeblocksafe(prefix)}```",
                    colour=self.bot.config.colours.neutral,
                )
            )

        if ctx.guild.id not in self.bot.prefixes:
            await self.bot.db.execute(
                "INSERT INTO prefixes VALUES($1, $2)", ctx.guild.id, [prefix]
            )
            self.bot.prefixes[ctx.guild.id] = [prefix]

        else:
            await self.bot.db.execute(
                "UPDATE prefixes SET prefixes = $1 WHERE guild_id = $2",
                [prefix],
                ctx.guild.id,
            )

        await ctx.embed(
            title="Done!",
            description=f"```\nSet the prefix to {codeblocksafe(prefix)}```",
            colour=self.bot.config.colours.good,
        )


def setup(bot: Nexus):
    bot.add_cog(Settings(bot))