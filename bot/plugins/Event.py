import discord
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot
from .utils.embed import NeutralEmbed


class Event(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

        guild = self.bot.config.get("dev", {})
        self.logs_channel = guild.get("guild-logs", None)
        if self.logs_channel:
            self.logs_channel = self.bot.get_channel(self.logs_channel)

    @commands.Cog.listener(name="on_guild_join")
    async def _on_guild_join(self, guild: discord.Guild) -> None:
        if whitelist := self.bot.config.get("guild-whitelist", None):
            if whitelist.get("enabled", False):
                if guild.id not in whitelist.get("guilds", []):
                    self.bot.logger.info(
                        f"Rejected addition to {guild.name} ({guild.id})"
                    )
                    await guild.leave()
        elif self.logs_channel:
            embed = (
                NeutralEmbed(title=f"Guild gained!")
                .add_field(name="Name", value=guild.name)
                .add_field(name="Id", value=guild.id)
                .add_field(name="Members count", value=guild.member_count)
                .add_field(name="Owner", value=guild.owner.mention)
            )
            await self.logs_channel.send(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Event(bot))
