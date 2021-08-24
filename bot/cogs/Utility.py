from io import BytesIO
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

    @is_owner()
    @command(name="screenshot", cls=Command, aliases=["ss"])
    async def _screenshot(self, ctx: NexusContext, url: str):
        """
        Screenshot a website
        """
        try:
            async with async_playwright() as playwright:
                await ctx.send("Creating browser")
                browser = await playwright.chromium.launch(headless=True)
                await ctx.send("Browser created")
                context = await browser.new_context()
            
            page = await context.new_page(
                geolocation={"latitude": 51.509865, "longitude": -0.118092},
                viewport={"width": 1920, "height": 1080},
                locale="en-GB",
                permissions=["geolocation"],
                accept_downloads=False,
            )
            await ctx.send("Page created")

            await page.goto(url)

            with suppress(TimeoutError):
                await page.click("text=I agree")

            buf = BytesIO(await page.screenshot())

            await ctx.send(file=File(buf, "screenshot.png"))

            await page.close()
        except Exception as e:
            await ctx.send(e)


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
