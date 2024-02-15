import typing
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot
from discord import app_commands
from .utils.embed import SuccessEmbed, ErrorEmbed
import logging


class ModerationError(Exception):
    """Base class for Moderation exceptions"""


class NoPermission(ModerationError):
    """I don't have permission to do that!"""


class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        self.logger = logging.getLogger("discord.bot.plugins.Moderation")

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original

        if isinstance(
            error,
            (NoPermission),
        ):
            message = error.__doc__

        elif isinstance(error, app_commands.TransformerError):
            message = f"Couldn't find a song matching '{error.value}'"

        else:
            message = f"An error occured. If the issue persists, please contact the support team."
            self.logger.error(
                str(error), exc_info=(type(error), error, error.__traceback__)
            )

        embed = ErrorEmbed(message)

        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="ban")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def _ban(
        self,
        interaction: discord.Interaction,
        member: discord.User,
        reason: typing.Optional[str],
    ) -> None:
        """Ban someone

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param member: Member to ban
        :type member: discord.User
        :param reason: Ban reason
        :type reason: typing.Optional[str]
        """
        reason = reason or "No reason provided"

        try:
            await interaction.guild.ban(member, reason=reason)
            await interaction.response.send_message(
                embed=SuccessEmbed(f"Banned {member}\nReason: {reason}")
            )
        except discord.Forbidden:
            raise NoPermission
        
    # @app_commands.command(name="unban")
    # @app_commands.checks.has_permissions(ban_members=True)
    # @app_commands.checks.bot_has_permissions(ban_members=True)
    


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
