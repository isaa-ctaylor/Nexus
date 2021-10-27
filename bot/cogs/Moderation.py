import asyncio
from contextlib import suppress
from typing import Callable, Optional, Union

from discord.channel import TextChannel
from discord.embeds import Embed
from discord.errors import Forbidden, HTTPException
from discord.ext.commands.core import (
    bot_has_guild_permissions,
    bot_has_permissions,
    command,
    group,
    guild_only,
    has_guild_permissions,
    has_permissions,
)
from discord.member import Member
from discord.message import Message
from discord.permissions import Permissions
from discord.user import User
from discord.utils import MISSING, get
from utils import codeblocksafe
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command, Group
from utils.subclasses.context import NexusContext


class Moderation(Cog):
    """
    Moderation commands
    """

    def __init__(self, bot: Nexus) -> None:
        self.bot = bot

        self.bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        cache = {}

        data = await self.bot.db.fetch("SELECT * FROM chatlimit", one=False)

        for record in data:
            if record["guild_id"] in cache:
                if record["channel_id"] in cache[record["guild_id"]]:
                    continue
            else:
                cache[record["guild_id"]] = {}
            cache[record["guild_id"]][record["channel_id"]] = record["num"]

        self.cache = cache

    @guild_only()
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
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
        Ban the given member for the optional reason

        Optionally delete messages sent in the last specified days

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
                    colour=self.bot.config.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Banning {codeblocksafe(member)} failed!")

    @guild_only()
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
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

        if ctx.author.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than you!"
            )

        if ctx.me.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than me!"
            )

        try:
            await ctx.guild.unban(
                member, reason=f"{ctx.author} ({ctx.author.id}): {reason}"
            )
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully unbanned {codeblocksafe(member)}```",
                    colour=self.bot.config.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Unbanning {codeblocksafe(member)} failed!")

    @guild_only()
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
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
            role = await ctx.guild.create_role(
                name="Muted",
                permissions=Permissions(66560),
                reason="Mute command needs Muted role",
            )
            for channel in ctx.guild.channels:
                await channel.set_permissions(
                    role, send_messages=False, read_messages=True, view_channel=False
                )

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
                    colour=self.bot.config.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Muting {codeblocksafe(member)} failed!")

    @guild_only()
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(name="unmute", cls=Command)
    async def _unmute(
        self,
        ctx: NexusContext,
        member: Member,
        *,
        reason: Optional[str] = "No reason provided",
    ):
        """
        Unmute the given member
        """

        if member.id == ctx.author.id:
            return await ctx.error("You cannot unmute yourself!")

        if ctx.author.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than you!"
            )

        if ctx.me.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than me!"
            )

        role = get(ctx.guild.roles, name="Muted")

        if not role or role not in member.roles:
            return await ctx.error(f"{codeblocksafe(member)} is not muted!")

        try:
            await member.remove_roles(
                role, reason=f"{ctx.author} ({ctx.author.id}): {reason}"
            )
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully unmuted {codeblocksafe(member)}```",
                    colour=self.bot.config.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Unmuting {codeblocksafe(member)} failed!")

    @guild_only()
    @has_guild_permissions(kick_members=True)
    @bot_has_guild_permissions(kick_members=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(
        name="kick",
        cls=Command,
        examples=["@Someone#1234", "718087881087910018 Swearing"],
    )
    async def _kick(
        self,
        ctx: NexusContext,
        member: Member,
        *,
        reason: Optional[str] = "No reason provided",
    ):
        """
        Kick the specified member from the server
        """

        if member.id == ctx.author.id:
            return await ctx.error("You can't kick yourself!")

        if ctx.author.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than you!"
            )

        if ctx.me.top_role < member.top_role:
            return await ctx.error(
                f"{codeblocksafe(member)} has a higher role than me!"
            )

        try:
            await ctx.guild.kick(member, reason=reason)
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully kicked {codeblocksafe(member)}```",
                    colour=self.bot.config.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error(f"Unmuting {codeblocksafe(member)} failed!")

    @guild_only()
    @has_permissions(manage_messages=True)
    @bot_has_permissions(manage_channels=True, send_messages=True, embed_links=True)
    @command(name="slowmode", cls=Command, examples=["#general 4", "10"])
    async def _slowmode(
        self,
        ctx: NexusContext,
        channel: Optional[TextChannel] = None,
        rate: Optional[int] = 0,
    ):
        """
        Change the slowmode for the specified or current channel

        Specify a channel before the rate to change the rate for that channel

        Maximum rate: 21600 (6 hours) (rates will be rounded to the max/min if over/under)
        """

        rate = max(min(rate, 21600), 0)
        channel = channel or ctx.channel

        try:
            await channel.edit(
                slowmode_delay=rate,
                reason=f"{ctx.author} ({ctx.author.id}): Slowmode command invoked",
            )
            await ctx.paginate(
                Embed(
                    title="Done!",
                    description=f"```\nSuccessfully changed the slowmode to {rate}```",
                    colour=self.bot.config.colours.good,
                )
            )
        except Forbidden:
            await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            await ctx.error("Changing slowmode failed!")

    async def _do_purge(
        self,
        ctx: NexusContext,
        channel: TextChannel,
        limit: int,
        check: Optional[Callable] = MISSING,
    ):
        try:
            messages = await channel.purge(limit=limit, check=check)
            await ctx.send(
                embed=Embed(
                    description=f"```\nDeleted {len(messages)}/{limit} messages```",
                    colour=self.bot.config.colours.good,
                ),
                delete_after=2,
            )
        except Forbidden:
            return await ctx.error("I couldn't do that for some reason!")
        except HTTPException:
            return await ctx.error("Purging failed!")

    @guild_only()
    @has_permissions(manage_messages=True)
    @bot_has_permissions(
        manage_messages=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
    )
    @group(
        name="purge",
        cls=Group,
        aliases=["clear", "cleanup"],
        examples=["#general 4", "@Someone#1234 15", "10"],
        invoke_without_command=True,
    )
    async def _purge(self, ctx: NexusContext, limit: Optional[int] = 10):
        """
        Purge messages from the current channel

        More functionality within the subcommands
        """
        await self._do_purge(ctx, ctx.channel, limit)

    @guild_only()
    @has_permissions(manage_messages=True)
    @bot_has_permissions(
        manage_messages=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
    )
    @_purge.command(name="user")
    async def _purge_user(
        self,
        ctx: NexusContext,
        user: Optional[Member] = None,
        limit: Optional[int] = 10,
    ):
        """
        Purge messages from a specified user or you, if not specified
        """

        user = user or ctx.author

        await self._do_purge(ctx, ctx.channel, limit, lambda m: m.author.id == user.id)

    @guild_only()
    @has_permissions(manage_messages=True)
    @bot_has_permissions(
        manage_messages=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
    )
    @command(cls=Command, name="chatlimit")
    async def _chatlimit(
        self, ctx: NexusContext, channel: Optional[TextChannel] = None, limit: int = 100
    ):
        """
        Set a limit to the number of messages in a channel

        Optionally specify the channel if it's not the current one
        Limit defaults to 100
        """
        channel = channel or ctx.channel

        if limit == 0:
            await self.bot.db.execute(
                "DELETE FROM chatlimit WHERE channel_id = $1", channel.id
            )
            self.bot.loop.create_task(
                ctx.embed(
                    title="Done!",
                    description=f"Disabled the chat limit for {channel.mention}.",
                )
            )
            return await self.__ainit__()

        if limit > 100 or limit < 5:
            return await ctx.error("Limit must be between 5 and 100 inclusive!")

        _cache = self.cache.copy()  # Prevent keys changing on iteration

        if channel.id in _cache.get(channel.guild.id, []):
            await self.bot.db.execute(
                "UPDATE chatlimit SET num = $2 WHERE channel_id = $3 AND guild_id = $1",
                ctx.guild.id,
                limit,
                channel.id,
            )

        else:
            await self.bot.db.execute(
                "INSERT INTO chatlimit VALUES($1, $2, $3)",
                ctx.guild.id,
                channel.id,
                limit,
            )

        self.bot.loop.create_task(
            ctx.embed(
                title="Done!",
                description=f"Set the chat limit for {channel.mention} to {limit}.",
            )
        )

        await self.__ainit__()

    @Cog.listener(name="on_message")
    async def limit_messages(self, message: Message):
        """
        Limits the messages in a channel according to limits set using the chatlimit command
        """
        with suppress(Exception):
            if (
                message.guild.id in self.cache
                and message.channel.id in self.cache[message.guild.id]
            ):
                history = await message.channel.history(
                    limit=100, oldest_first=True
                ).flatten()
                if len(history) >= self.cache[message.guild.id][message.channel.id] + 1:
                    if (
                        len(history)
                        > self.cache[message.guild.id][message.channel.id] + 1
                    ):
                        for i in range(
                            len(history)
                            - self.cache[message.guild.id][message.channel.id]
                            + 1
                        ):
                            await history[i].delete()
                    else:
                        await history[0].delete()


def setup(bot: Nexus):
    bot.add_cog(Moderation(bot))
