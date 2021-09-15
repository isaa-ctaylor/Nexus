from typing import Optional
from discord.channel import TextChannel
from discord.ext.commands.core import has_guild_permissions
from discord.message import Message
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import group
from utils.subclasses.context import NexusContext
from discord.embeds import Embed


class Modlogs(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

        self.cache = {}
        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        data = await self.bot.db.fetch("SELECT * FROM modlogs", one=False)

        self.cache = {
            record["guild_id"]: {
                "enabled": record["enabled"],
                "channel": record["channel"],
            }
            for record in data
        }

    @has_guild_permissions(manage_messages=True)
    @group(name="modlogs", invoke_without_command=True)
    async def _modlogs(self, ctx: NexusContext):
        """
        Change modlog settings.
        Functionality in the subcommands.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @has_guild_permissions(manage_messages=True)
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

        await self.__ainit__()

        await ctx.paginate(
            Embed(
                title="Done!",
                description="Modlogs are now `enabled`!",
                colour=self.bot.config.colours.neutral,
            )
        )

    @has_guild_permissions(manage_messages=True)
    @_modlogs.command(name="disable")
    async def _modlogs_disable(self, ctx: NexusContext):
        """
        Disable modlogs.
        """
        if (
            ctx.guild.id not in self.cache
            or not self.cache[ctx.guild.id]["enabled"]
        ):
            return await ctx.error("Modlogs are not enabled!")

        await self.bot.db.execute(
            "UPDATE modlogs SET enabled = 'false' WHERE guild_id = $1", ctx.guild.id
        )

        await self.__ainit__()

        await ctx.paginate(
            Embed(
                title="Done!",
                description="Modlogs are now `disabled`!",
                colour=self.bot.config.colours.neutral,
            )
        )
        
    @has_guild_permissions(manage_messages=True)
    @_modlogs.command(name="channel")
    async def _modlogs_channel(self, ctx: NexusContext, channel: Optional[TextChannel] = None):
        channel = channel or ctx.channel
        
        if ctx.guild.id not in self.cache:
            return await ctx.error("Modlogs are not set up!")
        
        await self.bot.db.execute("UPDATE modlogs SET channel = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        
        await ctx.paginate(Embed(title="Done!", description=f"Set the modlogs channel to {channel.mention}!", colour=self.bot.config.colours.neutral))

    @Cog.listener(name="on_message_delete")
    async def _log_message_delete(self, message: Message):
        ...


def setup(bot: Nexus):
    bot.add_cog(Modlogs(bot))