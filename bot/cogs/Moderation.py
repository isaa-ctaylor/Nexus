from discord.embeds import Embed
from discord.errors import Forbidden, HTTPException
from discord.ext.commands.converter import UserConverter
from discord.permissions import Permissions
from discord.utils import get
from requests.models import HTTPError
from utils.subclasses.context import NexusContext
from typing import Optional, Union
from discord.user import User
from discord.ext.commands.core import (
    bot_has_guild_permissions,
    command,
    has_guild_permissions,
)
from discord.member import Member
from discord.object import Object
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from utils.subclasses.command import Command
from utils import codeblocksafe


class Moderation(Cog):
    """
    Moderation commands
    """
    def __init__(self, bot: Nexus) -> None:
        self.bot = bot

    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @command(
        name="ban",
        cls=Command,
        usage="<member> [days to delete messages] [reason]",
        examples=["@isaa_ctaylor#2494 Swearing", "718087881087910018"],
    )
    async def _ban(
        self,
        ctx: NexusContext,
        member: Union[Member, User],
        delete_days: Optional[int] = 0,
        *,
        reason: Optional[str] = "No reason provided",
    ):
        """
        Ban the given member for the optional reason, optionally deleting messages sent in the last specified days

        The member in question can be supplied with a mention (e.g. @isaa_ctaylor#2494),
        a name (if they are in the server) (e.g. isaa_ctaylor) or an id (e.g. 718087881087910018)
        """
        
        if member.id == ctx.author.id:
            return await ctx.error("You cannot ban yourself!")

        if delete_days < 0 or delete_days > 7:
            await ctx.error("You can only delete messages from a range 0-7 days!")

        try:
            await ctx.guild.ban(
                member,
                delete_message_days=delete_days,
                reason=f"{ctx.author} ({ctx.author.id}): {reason}",
            )
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully banned {codeblocksafe(member)}```",
                    colour=self.bot.config.data.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Banning {codeblocksafe(member)} failed!")

    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @command(
        name="unban",
        cls=Command,
        examples=["718087881087910018 Appeal approved", "718087881087910018"],
    )
    async def _unban(
        self,
        ctx: NexusContext,
        member: User,
        *,
        reason: Optional[str] = "No reason provided",
    ):
        """
        Unban the currently banned member via id, for the optional reason
        """
        
        if member.id == ctx.author.id:
            return await ctx.error("You cannot unban yourself!")

        try:
            await ctx.guild.unban(
                member, reason=f"{ctx.author} ({ctx.author.id}): {reason}"
            )
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully unbanned {codeblocksafe(member)}```",
                    colour=self.bot.config.data.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Unbanning {codeblocksafe(member)} failed!")

    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    @command(
        name="mute", cls=Command, examples=["718087881087910018", "@Person#0123 spam"]
    )
    async def _mute(
        self,
        ctx: NexusContext,
        member: Member,
        *,
        reason: Optional[str] = "No reason provided",
    ):
        """
        Mute the given member for the optional reason

        Note: If this command does not seem to work, make sure the person does not have the Speak permission for the channel, and that they do not have any other roles with the speak permission
        """
        
        if member.id == ctx.author.id:
            return await ctx.error("You cannot mute yourself!")


        if ctx.author.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than you!"
            )

        if ctx.me.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than me!"
            )

        role = get(ctx.guild.roles, name="Muted")

        if not role:
            role = await ctx.guild.create_role(name="Muted", permissions=Permissions(66560), reason="Mute command needs Muted role")
            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, read_messages=True, view_channel=False)

        if role in member.roles:
            return await ctx.error(f"{codeblocksafe(member)} is already muted!")

        try:
            await member.add_roles(
                role, reason=f"{ctx.author} ({ctx.author.id}): {reason}"
            )
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully muted {codeblocksafe(member)}```",
                    colour=self.bot.config.data.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Muting {codeblocksafe(member)} failed!")
            
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    @command(name="unmute", cls=Command)
    async def _unmute(self, ctx: NexusContext, member: Member, *, reason: Optional[str] = "No reason provided"):
        """
        Unmute the given member
        """
        
        if member.id == ctx.author.id:
            return await ctx.error("You cannot unmute yourself!")


        role = get(ctx.guild.roles, name="Muted")

        if not role or role not in member.roles:
            return await ctx.error(f"{codeblocksafe(member)} is not muted!")

        try:
            await member.remove_roles(role, reason=f"{ctx.author} ({ctx.author.id}): {reason}")
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully unmuted {codeblocksafe(member)}```",
                    colour=self.bot.config.data.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Unmuting {codeblocksafe(member)} failed!")


def setup(bot: Nexus):
    bot.add_cog(Moderation(bot))
