from discord.file import File
from utils.subclasses.context import NexusContext
from discord.ext.commands.core import is_owner
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from playwright.async_api import async_playwright
from utils.subclasses.command import command, Command
from playwright._impl._api_types import TimeoutError
from contextlib import suppress


class Utility(Cog):
    def __init__(self, bot: Nexus):
        self.bot = Nexus
        
        bot.loop.create_task(self.__ainit__())
        
    async def __ainit__(self):
        async with async_playwright() as playwright:
            self.browser = await playwright.chromium.launch()
    
    @is_owner()
    @command(name="screenshot", cls=Command, aliases=["ss"])
    async def _screenshot(self, ctx: NexusContext, url: str):
        """
        Screenshot a website
        """
        page = await self.browser.new_page(geolocation={"latitude": 51.509865, "longitude": -0.118092}, viewport={"width": 1920, "height": 1080})

        await page.goto(url)
        
        with suppress(TimeoutError):
            await page.click("text=I agree")

        buf = await page.screenshot()
        
        await ctx.send(file=File(buf, "screenshot.png"))

        await page.close()


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
