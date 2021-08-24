from asyncio.events import get_event_loop
from functools import partial
from io import BytesIO
from typing import Callable, Optional
from discord.file import File
from utils.subclasses.context import NexusContext
from discord.ext.commands.core import is_owner
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from playwright.sync_api import sync_playwright
from utils.subclasses.command import command, Command
from playwright._impl._api_types import TimeoutError
from contextlib import suppress


bot: Optional[Nexus] = None


def execute(self, func: Callable):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await bot.loop.run_in_executor(None, partial(func, *args, **kwargs))

    return wrapper


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


def setup(_bot: Nexus):
    _bot.add_cog(Utility(_bot))
    
    global bot
    bot = _bot
