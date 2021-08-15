from discord.embeds import Embed
from discord.ext.commands.cooldowns import BucketType, CooldownMapping
from discord.ext.commands.core import (bot_has_permissions, group,
                                       has_guild_permissions)
from discord.message import Message
from utils.helpers import DotDict
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command, Group, command
from utils.subclasses.context import NexusContext


class Automod(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.cooldown = CooldownMapping.from_cooldown(10, 12, BucketType.user)

        bot.loop.run_until_complete(self.__ainit__())

    async def __ainit__(self):
        automoddata = [
            dict(record)
            for record in self.bot.db.fetch("SELECT * FROM automod", one=False)
        ]
        spamcheckerdata = [
            dict(record)
            for record in self.bot.db.fetch("SELECT * FROM spamchecker", one=False)
        ]

        _cache = {
            record["guild_id"]: {"enabled": record["enabled"]} for record in automoddata
        }

        for record in spamcheckerdata:
            if record["guild_id"] not in _cache:
                _cache[record["guild_id"]] = {"enabled": False}
                self.bot.db.execute(
                    "INSERT INTO automod(guild_id, enabled) VALUES($1, $2)",
                    record["guild_id"],
                    False,
                )

            _cache[record["guild_id"]]["spam"] = {"enabled": record["enabled"]}

        self.cache = DotDict(_cache)

    @Cog.listener(name="on_message")
    async def _auto_message_response(self, message: Message):
        if not message.guild:
            return

        if message.author.id != self.bot.owner_id:
            return

        bucket = self.cooldown.get_bucket(message)

        if bucket.update_rate_limit(message.created_at.timestamp()):
            await message.reply("Stop spamming!")

    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    @group(name="automod", cls=Group)
    async def _automod(self, ctx: NexusContext):
        """
        See the current automod settings

        Other functionality in the subcommands
        """
        await ctx.send_help(ctx.command)

    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(send_messages=True, embed_links=True)
    @_automod.group(name="spam")
    async def _automod_spam(self, ctx: NexusContext):
        """
        See the current spam settings
        """
        embed = Embed(
            title="Spam settings", colour=self.bot.config.data.colours.neutral
        )
        embed.add_field(
            name="Enabled",
            value=f"```\n{'Yes' if self.cache[ctx.guild.id].spam.enabled else 'No'}```",
        )

        await ctx.paginate(embed)

def setup(bot: Nexus):
    bot.add_cog(Automod(bot))
