import discord
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot

class Event(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener(name="on_guild_join")
    async def _on_guild_join(self, guild: discord.Guild) -> None:
        if whitelist := self.bot.config.get("guild-whitelist", None):
            if whitelist.get("enabled", False):
                if guild.id not in whitelist.get("guilds", []):
                    self.bot.logger.info(f"Rejected addition to {guild.name} ({guild.id})")
                    await guild.leave()

async def setup(bot: Bot):
    await bot.add_cog(Event(bot))