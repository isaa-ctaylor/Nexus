from discord.guild import Guild
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog


class Listeners(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    @Cog.listener(name="on_guild_join")
    async def _guild_join(self, guild: Guild):
        await self.bot.db.execute(
            """INSERT INTO automod(guild_id) VALUES($1)
            ON CONFLICT (guild_id) 
            DO UPDATE 
            SET enabled = 'false'
            WHERE prefixes.guild_id = $1""",
            guild.id,
        )


def setup(bot: Nexus):
    bot.add_cog(Listeners(bot))
