from traceback import format_exception
from typing import List, Optional
from discord.abc import GuildChannel
from discord.channel import TextChannel
from discord.enums import AuditLogAction
from discord.errors import Forbidden, HTTPException
from discord.ext.commands.core import has_guild_permissions
from discord.guild import Guild
from discord.message import Message
from discord.role import Role
from discord.utils import utcnow
from discord.webhook.async_ import Webhook
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import group
from utils.subclasses.context import NexusContext
from discord.embeds import Embed
from contextlib import suppress
import utils


class Modlogs(Cog):
    """
    Log moderation actions in your server
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

        self.cache = {}
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        data = await self.bot.db.fetch("SELECT * FROM modlogs", one=False)

        self.cache = {
            record["guild_id"]: {
                "enabled": record["enabled"],
                "channel": Webhook.from_url(
                    str(record["channel"]).strip(), session=self.bot.session
                ),
            }
            for record in data
        }

    @group(name="modlogs", invoke_without_command=True)
    async def _modlogs(self, ctx: NexusContext):
        """
        Change modlog settings.
        Functionality in the subcommands.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @has_guild_permissions(manage_guild=True)
    @_modlogs.command(name="enable")
    async def _modlogs_enable(self, ctx: NexusContext):
        """
        Enable modlogs.
        """
        if ctx.guild.id not in self.cache:
            await self.bot.db.execute(
                "INSERT INTO modlogs(guild_id) VALUES($1)", ctx.guild.id
            )
            self.cache[ctx.guild.id] = {"enabled": False, "channel": None}

        if self.cache[ctx.guild.id]["enabled"]:
            return await ctx.error("Modlogs are already enabled!")

        await self.bot.db.execute(
            "UPDATE modlogs SET enabled = 'true' WHERE guild_id = $1", ctx.guild.id
        )

        self.bot.loop.create_task(self.__ainit__())

        await ctx.paginate(
            Embed(
                title="Done!",
                description="Modlogs are now `enabled`!",
                colour=self.bot.config.colours.neutral,
            )
        )

    @has_guild_permissions(manage_guild=True)
    @_modlogs.command(name="disable")
    async def _modlogs_disable(self, ctx: NexusContext):
        """
        Disable modlogs.
        """
        if ctx.guild.id not in self.cache or not self.cache[ctx.guild.id]["enabled"]:
            return await ctx.error("Modlogs are not enabled!")

        await self.bot.db.execute(
            "UPDATE modlogs SET enabled = 'false' WHERE guild_id = $1", ctx.guild.id
        )

        self.bot.loop.create_task(self.__ainit__())

        await ctx.paginate(
            Embed(
                title="Done!",
                description="Modlogs are now `disabled`!",
                colour=self.bot.config.colours.neutral,
            )
        )

    @has_guild_permissions(manage_guild=True)
    @_modlogs.command(name="channel")
    async def _modlogs_channel(
        self, ctx: NexusContext, channel: Optional[TextChannel] = None
    ):
        """
        Set the channel for modlogs to go to
        """
        channel = channel or ctx.channel

        if ctx.guild.id not in self.cache:
            return await ctx.error("Modlogs are not set up!")

        try:
            wh = await channel.create_webhook(
                name="Nexus", avatar=await self.bot.user.avatar.read(), reason="Logging"
            )
        except (Forbidden, HTTPException):
            return await ctx.error(
                f"I need the Manage webhooks permission in {channel.name}!"
            )

        await self.bot.db.execute(
            "UPDATE modlogs SET channel = $1 WHERE guild_id = $2",
            wh.url,
            ctx.guild.id,
        )

        self.bot.loop.create_task(self.__ainit__())

        await ctx.paginate(
            Embed(
                title="Done!",
                description=f"Set the modlogs channel to {channel.mention}!",
                colour=self.bot.config.colours.neutral,
            )
        )

    async def _send(self, guild: Guild, *args, **kwargs):
        if kwargs.get("embed", None) is not None:
            kwargs["embed"].timestamp = utcnow()

        c: Webhook = self.cache[guild.id]["channel"]
        if c:
            await c.send(*args, **kwargs)

    @Cog.listener(name="on_message_delete")
    async def _log_message_delete(self, message: Message):
        with suppress(Exception):
            if not (
                message.guild.id in self.cache
                and self.cache[message.guild.id]["enabled"]
            ):
                return

            channel = self.cache[message.guild.id]["channel"]

            if not channel:
                return

            embed = (
                Embed(title="Message deleted", colour=self.bot.config.colours.neutral)
                .add_field(name="Channel", value=message.channel.mention)
                .add_field(name="Author", value=message.author.mention)
                .add_field(
                    name="Content",
                    value=message.content or "This message contained no content.",
                    inline=False,
                )
                .set_footer(text=str(message.id))
            )

            await self._send(message.guild, embed=embed)

    @Cog.listener(name="on_bulk_message_delete")
    async def _log_bulk_message_delete(self, messages: List[Message]):
        with suppress(Exception):
            if not (
                messages[0].guild.id in self.cache
                and self.cache[messages[0].guild.id]["enabled"]
            ):
                return

            channel = self.cache[messages[0].guild.id]["channel"]

            if not channel:
                return

            embed = (
                Embed(
                    title="Bulk messages deleted",
                    colour=self.bot.config.colours.neutral,
                )
                .add_field(name="Channel", value=messages[0].channel.mention)
                .add_field(name="Quantity", value=len(messages))
                .add_field(
                    name="Authors",
                    value=utils.naturallist(set([m.author for m in messages])),
                    inline=False,
                )
            )

            await self._send(messages[0].guild, embed=embed)

    @Cog.listener(name="on_message_edit")
    async def _log_message_edit(self, before: Message, after: Message):
        with suppress(Exception):
            if before.content == after.content:
                return

            if not (
                after.guild.id in self.cache and self.cache[after.guild.id]["enabled"]
            ):
                return

            channel = self.cache[after.guild.id]["channel"]

            if not channel:
                return

            embed = (
                Embed(title="Message edited", colour=self.bot.config.colours.neutral)
                .add_field(name="Channel", value=after.channel.mention)
                .add_field(name="Author", value=after.author.mention)
                .add_field(name="Content before", value=before.content, inline=False)
                .add_field(name="Content after", value=after.content, inline=True)
                .set_footer(text=str(after.id))
            )

            await self._send(after.guild, embed=embed)

    @Cog.listener(name="on_guild_channel_create")
    async def _log_channel_creation(self, channel: GuildChannel):
        with suppress(Exception):
            if not (
                channel.guild.id in self.cache
                and self.cache[channel.guild.id]["enabled"]
            ):
                return

            _channel = self.cache[channel.guild.id]["channel"]

            if not _channel:
                return

            embed = Embed(
                title="Channel created", colour=self.bot.config.colours.neutral
            )
            embed.add_field(name="Channel name", value=channel.name, inline=True)
            embed.add_field(
                name="Channel category",
                value=channel.category.name if channel.category else "None",
                inline=True,
            )
            embed.set_footer(text=str(channel.id))

            tick = self.bot.config.emojis.tick
            cross = self.bot.config.emojis.cross

            if channel.overwrites:
                permissions = {
                    obj: {
                        overwrite: v
                        for overwrite, v in dict(overwrites).items()
                        if v in [True, False]
                    }
                    for obj, overwrites in channel.overwrites.items()
                }

                embed.description = "\n\n".join(
                    f"**Overwrites for {obj.mention if not (isinstance(obj, Role) and obj.is_default()) else '@everyone'}:**\n"
                    + "\n".join(
                        f"{tick if v else cross} {k.replace('_', ' ').capitalize()}"
                        for k, v in overwrites.items()
                    )
                    for obj, overwrites in permissions.items()
                )

            await self._send(channel.guild, embed=embed)

    @Cog.listener(name="on_guild_channel_delete")
    async def _log_channel_deletion(self, channel: GuildChannel):
        with suppress(Exception):
            if not (
                channel.guild.id in self.cache
                and self.cache[channel.guild.id]["enabled"]
            ):
                return

            _channel = self.cache[channel.guild.id]["channel"]

            if not _channel:
                return

            embed = Embed(
                title="Channel deleted", colour=self.bot.config.colours.neutral
            )
            embed.add_field(name="Channel name", value=channel.name, inline=True)
            embed.add_field(
                name="Channel category",
                value=channel.category.name if channel.category else "None",
                inline=True,
            )
            embed.set_footer(text=str(channel.id))

            await self._send(channel.guild, embed=embed)

    @Cog.listener(name="on_guild_channel_edit")
    async def _log_channel_edit(self, before: GuildChannel, after: GuildChannel):
        ...


async def setup(bot: Nexus):
    await bot.add_cog(Modlogs(bot))
    
