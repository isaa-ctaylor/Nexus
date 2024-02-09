import discord
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot
import typing
from .utils.embed import ErrorEmbed


class Error(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener(name="on_error")
    async def _on_error(self, error: discord.DiscordException):
        raise error

    @commands.Cog.listener(name="on_command_error")
    async def _on_command_error(
        self,
        ctx: commands.Context,
        error: typing.Union[commands.CommandInvokeError, discord.DiscordException],
    ) -> None:
        error_ = error
        if isinstance(error, commands.CommandInvokeError):
            error_ = error.original

        if isinstance(error_, commands.CommandNotFound):
            return

        if getattr(error_, "message", None):
            message = error_.message

        else:
            message = str(error_)

        await ctx.reply(embed=ErrorEmbed(message))

        if not ctx.author.id == self.bot.owner_id:
            # Allow error to be picked up by sentry
            # Unless it originated from the bot owner because I'm probably messing around
            raise error


async def setup(bot: Bot):
    await bot.add_cog(Error(bot))
