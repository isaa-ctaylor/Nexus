from utils import execute
from io import BytesIO
from discord.file import File
from utils.subclasses.context import NexusContext
from discord.ext.commands.core import is_owner
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from playwright.sync_api import sync_playwright
from utils.subclasses.command import command, Command
from playwright._impl._api_types import TimeoutError
from contextlib import suppress


class Utility(Cog):
    def __init__(self, bot: Nexus):
        self.bot = Nexus

    @execute
    def _do_screenshot(self, url):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)

        page = browser.new_page(
            geolocation={"latitude": 51.509865, "longitude": -0.118092},
                viewport={"width": 1920, "height": 1080},
                locale="en-GB",
                permissions=["geolocation"],
                accept_downloads=False,
        )
        
        page.goto(url)

        with suppress(TimeoutError):
            page.click("text=I agree")

        return BytesIO(page.screenshot())


    @is_owner()
    @command(name="screenshot", cls=Command, aliases=["ss"])
    async def _screenshot(self, ctx: NexusContext, url: str):
        """
        Screenshot a website
        """
        try:
            await ctx.send(file=File(await self._do_screenshot(url), "screenshot.png"))
        except Exception as e:
            await ctx.send(e)


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
