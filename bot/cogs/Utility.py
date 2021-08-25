from discord.embeds import Embed
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext
from utils.subclasses.command import command, Command
from async_timeout import timeout
from aiohttp import InvalidURL


class Utility(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    @command(name="redirectcheck", cls=Command, aliases=["redirects", "linkcheck"])
    async def _redirectcheck(self, ctx: NexusContext, url: str):
        async with ctx.typing():
            try:
                async with timeout(30):
                    async with self.bot.session.get(url) as resp:
                        history = list(resp.history)
                        history.append(resp)
                        
                        urls = "\n".join(str(url.url) if "grabify" not in str(url.url) else f"⚠ {url.url}" for url in history[1:])
            
            except TimeoutError:
                return await ctx.error("The request timed out!")
            
            except InvalidURL:
                return await ctx.error("Invalid url!")

        if urls:
            await ctx.paginate(Embed(description=f"```\n{urls}```\n{'This link contains a grabify redirect and could be being used maliciously. Proceed with care.' if '⚠' in urls else ''}", colour=self.bot.config.data.colours.neutral))
        else:
            await ctx.error(f"{url} does not redirect!")


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
