import datetime
import logging
import typing

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot

from .utils.embed import ErrorEmbed, SuccessEmbed, NeutralEmbed
from .utils.view import Confirm


class ModerationError(Exception):
    """Base class for Moderation exceptions"""


class NoPermission(ModerationError):
    """I don't have permission to do that!"""


class UserNotFound(ModerationError):
    """User not found! Please check the name or id provided"""


class BanNotFound(ModerationError):
    """Ban not found! Please check the name or id provided"""


class MemberHigherThanMe(ModerationError):
    """The requested user has a higher role than me!"""


class MemberIsBot(ModerationError):
    """Selected member is me!"""


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
            (NoPermission, UserNotFound, BanNotFound, MemberHigherThanMe, MemberIsBot),
        ):
            message = error.__doc__

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

    async def verify_roles(
        self,
        interaction: discord.Interaction,
        member: typing.Union[discord.Member, discord.User],
    ) -> None:
        if member.top_role > interaction.guild.me.top_role:
            raise MemberHigherThanMe

        if member.id == interaction.guild.me.id:
            raise MemberIsBot

    @app_commands.command(name="ban")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def _ban(
        self,
        interaction: discord.Interaction,
        member: discord.User,
        reason: typing.Optional[str],
    ) -> None:
        """Ban a member

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
                embed=SuccessEmbed(f"Banned {member.mention}\nReason: {reason}"),
                ephemeral=True,
            )
        except discord.Forbidden:
            raise NoPermission
        except discord.NotFound:
            raise UserNotFound

    @app_commands.command(name="unban")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.checks.bot_has_permissions(ban_members=True)
    async def _unban(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        reason: typing.Optional[str],
    ) -> None:
        """Unban a user

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param user: User to unban
        :type user: discord.User
        :param reason: Reason for unban
        :type reason: typing.Optional[str]
        """
        reason = reason or "No reason provided"

        try:
            await interaction.guild.unban(user, reason=reason)
            await interaction.response.send_message(
                embed=SuccessEmbed(f"Unbanned {user.mention}\nReason: {reason}"),
                ephemeral=True,
            )
        except discord.Forbidden:
            raise NoPermission
        except discord.NotFound:
            raise BanNotFound

    @app_commands.command(name="kick")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.checks.bot_has_permissions(kick_members=True)
    async def _kick(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: typing.Optional[str],
    ) -> None:
        """Kick a member

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param member: User to kick
        :type member: discord.Member
        :param reason: Reason for kick
        :type reason: typing.Optional[str]
        """
        reason = reason or "No reason provided"

        try:
            await interaction.guild.kick(member, reason=reason)
            await interaction.response.send_message(
                embed=SuccessEmbed(f"Kicked {member.mention}\nReason: {reason}"),
                ephemeral=True,
            )
        except discord.Forbidden:
            raise NoPermission
        except discord.NotFound:
            raise UserNotFound

    @app_commands.command(name="timeout")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.checks.bot_has_permissions(moderate_members=True)
    @app_commands.choices(
        duration=[
            app_commands.Choice(name="Remove", value=0),
            app_commands.Choice(name="60 seconds", value=60),
            app_commands.Choice(name="5 minutes", value=300),
            app_commands.Choice(name="10 minutes", value=600),
            app_commands.Choice(name="1 hour", value=3600),
            app_commands.Choice(name="1 day", value=86400),
            app_commands.Choice(name="1 week", value=604800),
        ]
    )
    async def _timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: app_commands.Choice[int],
        reason: typing.Optional[str],
    ) -> None:
        """Timeout a member

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param member: Member to timeout
        :type member: discord.Member
        :param reason: Reason for timeout
        :type reason: typing.Optional[str]
        """
        await self.verify_roles(interaction, member)

        if duration.value != 0:
            duration_ = datetime.timedelta(seconds=duration.value)
        else:
            duration_ = None

        reason = reason or "No reason provided"

        try:
            await member.timeout(duration_, reason=reason)
            await interaction.response.send_message(
                embed=SuccessEmbed(
                    f"Timed {member.mention} out for {duration.name} \nReason: {reason}"
                ),
                ephemeral=True,
            )
        except discord.Forbidden:
            raise NoPermission
        except discord.NotFound:
            raise UserNotFound

    @app_commands.command(name="nuke")
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    @app_commands.checks.bot_has_permissions(
        manage_channels=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
    )
    async def _nuke(
        self,
        interaction: discord.Interaction,
        channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Completely clear a channel by cloning it and deleting the original

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param channel: Channel to delete
        :type channel: discord.TextChannel
        """
        c = Confirm()
        await interaction.response.send_message(
            embed=NeutralEmbed(message=f"Please confirm you want to ")
        )
        c.message = await interaction.original_response()

        channel = channel or interaction.channel

        c = await channel.clone(
            reason=f"Nuke command invoked by @{interaction.user} ({interaction.user.id})"
        )
        await c.edit(position=channel.position)
        await channel.delete()

        await c.send(interaction.user.mention, delete_after=5)


async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))
