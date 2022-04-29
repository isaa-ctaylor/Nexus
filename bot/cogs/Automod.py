import asyncio
from discord.embeds import Embed
from discord.ext.commands.cooldowns import BucketType, CooldownMapping
from discord.ext.commands.core import bot_has_permissions, has_guild_permissions
from discord.message import Message
from utils.helpers import DotDict
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import command, group
from utils.subclasses.context import NexusContext


class Automod(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self.cooldown = CooldownMapping.from_cooldown(10, 12, BucketType.user)

        bot.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        automoddata = [
            dict(record)
            for record in await self.bot.db.fetch("SELECT * FROM automod", one=False)
        ]
        spamcheckerdata = [
            dict(record)
            for record in await self.bot.db.fetch(
                "SELECT * FROM spamchecker", one=False
            )
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


async def setup(bot: Nexus):
    await bot.add_cog(Automod(bot))
