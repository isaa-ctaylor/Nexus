import discord
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot
from typing import Optional, Literal

class Developer(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.is_owner()
    @commands.command(name="sync")
    async def _sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object], spec: Optional[Literal["~", "*", "^", "^*"]] = None) -> None:
        if not guilds:
            if spec == "~":
                synced = await self.bot.tree.sync(guild=ctx.guild)
            elif spec == "*":
                self.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await self.bot.tree.sync(guild=ctx.guild)
            elif spec == "^":
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                synced = []
            elif spec == "^*":
                self.bot.tree.clear_commands(guild=None)
                await self.bot.tree.sync()
            else:
                synced = await self.bot.tree.sync()

            await ctx.send(
                f"Synced {len(synced)} commands {'globally' if spec in [None, '^*'] else 'to the current guild.'}"
            )
            return

        ret = 0
        for guild in guilds:
            try:
                await self.bot.tree.sync(guild=guild)
            except discord.HTTPException:
                pass
            else:
                ret += 1

        await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

async def setup(bot: Bot):
    await bot.add_cog(Developer(bot))

