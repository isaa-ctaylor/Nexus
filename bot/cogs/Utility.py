from io import BytesIO
from math import floor, log10
from typing import Any, Optional

from topgg.types import BotVoteData

import pytesseract
from aiohttp import InvalidURL
from async_timeout import timeout
from discord import ButtonStyle
from discord.embeds import Embed
from discord.ext.commands import Converter
from discord.ext.commands.converter import UserConverter
from discord.ext.commands.errors import BadArgument
from discord.ui import Button, View
from PIL import Image, ImageOps, UnidentifiedImageError
from utils import Timer, codeblocksafe, executor
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command, command
from utils.subclasses.context import NexusContext


class InvalidDiscriminator(BadArgument):
    def __init__(self, arg: Any):
        self.arg = arg

    def __str__(self):
        return f"{codeblocksafe(self.arg)} is not a valid discriminator!"


class Discriminator(Converter):
    """
    A converter to validate discriminators
    """

    async def convert(self, ctx: NexusContext, argument: Any):
        _str = str(argument)

        if len(_str) != 4:
            try:
                return str((await UserConverter().convert(ctx, argument)).discriminator)
            except:
                return InvalidDiscriminator(argument)

        if not _str.isdigit():
            return InvalidDiscriminator(argument)

        return _str


class Utility(Cog):
    """
    Useful commands
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

    @command(
        name="redirectcheck",
        cls=Command,
        aliases=["redirects", "linkcheck"],
        examples=["https://youtu.be/"],
    )
    async def _redirectcheck(self, ctx: NexusContext, url: str):
        """
        Check redirects on a link

        This tool will warn you if the link contains a grabify link
        """

        try:
            async with ctx.typing():
                async with timeout(30):
                    async with self.bot.session.get(url) as resp:
                        history = list(resp.history)
                        history.append(resp)

                        urls = "\n".join(
                            str(url.url)
                            if "grabify.link" not in str(url.url)
                            or "iplogger.org" not in str(url.url)
                            else f"⚠ {url.url}"
                            for url in history[1:]
                        )

        except TimeoutError:
            return await ctx.error("The request timed out!")

        except InvalidURL:
            return await ctx.error("Invalid url!")

        if urls:
            message = f"WARNING! This link contains {'a grabify.link' if 'grabify.link' in urls else 'an iplogger.org' if 'iplogger.org' in urls else 'a logging'} redirect and could be being used maliciously. Proceed with caution."
            await ctx.paginate(
                Embed(
                    description=f"```\n{urls}```\n{message if '⚠' in urls else ''}".strip(),
                    colour=self.bot.config.colours.neutral,
                )
            )
        else:
            await ctx.error(f"{url} does not redirect!")

    @command(
        name="discriminator",
        cls=Command,
        aliases=["discrim"],
        examples=["0000", "1234"],
    )
    async def _discriminator(
        self, ctx: NexusContext, discriminator: Optional[Discriminator] = None
    ):
        """
        Show all members that the bot can see with the given discriminator.
        This tool can be used if you are trying to change your discriminator, by changing your name to an existing name.

        Defaults to the author's discriminator.
        """
        if isinstance(discriminator, InvalidDiscriminator):
            return await ctx.error(str(discriminator))

        if not discriminator:
            discriminator = ctx.author.discriminator

        async with ctx.typing():
            users = list(
                sorted(
                    [
                        m
                        for m in self.bot.users
                        if str(m.discriminator) == str(discriminator)
                    ],
                    key=lambda m: str(m),
                )
            )

            if not users:
                return await ctx.error(
                    f"There are no users with the discriminator {discriminator}!"
                )

            pages = [
                Embed(
                    title=f"Users with discriminator {discriminator}",
                    description="\n".join(f"`{codeblocksafe(m)} ({m.id})`" for m in _),
                    colour=self.bot.config.colours.neutral,
                )
                if i == 0
                else Embed(
                    description="\n".join(f"`{codeblocksafe(m)} ({m.id})`" for m in _),
                    colour=self.bot.config.colours.neutral,
                )
                for i, _ in enumerate(
                    users[i : i + 10] for i in range(0, len(users), 10)
                )
            ]

        await ctx.paginate(pages)

    @command(name="ping", cls=Command)
    async def _ping(self, ctx: NexusContext):
        embed = Embed(title="Pong!", colour=self.bot.config.colours.neutral)
        _ = self.bot.latency
        embed.add_field(name="Websocket", value=f"```py\n{round(_ * 1000, 2)}ms```")
        embed.add_field(name="Typing", value="```py\nPinging...```")
        _ = await self.bot.db.ping
        embed.add_field(
            name="Database", value=f"```py\n{round(_, -int(floor(log10(abs(_)))))}ms```"
        )

        with Timer() as t:
            m = await ctx.reply(embed=embed, mention_author=False)
            t.end()

            embed.remove_field(1)
            embed.insert_field_at(
                1, name="Typing", value=f"```py\n{round(t.elapsed, 2)}ms```"
            )

        await m.edit(embed=embed)

    @executor
    def _do_ocr(self, image):
        config = r"--oem 1 --tessdata-dir /opt/tessdata"
        return pytesseract.image_to_string(image, config=config)

    @command(name="ocr", cls=Command)
    async def _ocr(self, ctx: NexusContext, *, image: str = None):
        """
        Read text from an image

        If just supplying the image does not work, or the image is light text on a dark background, try adding "--invert" to the end of your message
        """
        invert = False
        if image:
            if "--invert" in image:
                invert = True
                image = image.replace("--invert", "")
            if image:
                try:
                    async with self.bot.session.get(image.strip()) as resp:
                        image = await resp.read()
                except InvalidURL:
                    return await ctx.error("Please attach a valid image!")

        if not image:
            if ctx.message.attachments:
                image = await ctx.message.attachments[0].read()
            if ref := ctx.message.reference:
                if attachments := ref.resolved.attachments:
                    image = await attachments[0].read()

        try:
            image = Image.open(BytesIO(image)).convert("RGB")
        except (TypeError, UnidentifiedImageError):
            return await ctx.error("Please attach a valid image!")

        if invert:
            image = ImageOps.invert(image)

        async with ctx.typing():
            embed = Embed(
                description=await self._do_ocr(image),
                colour=self.bot.config.colours.neutral,
            )

        await ctx.paginate(embed)

    @command(cls=Command, name="vote")
    async def _vote(self, ctx: NexusContext):
        """
        Vote for Nexus!
        """
        embed = Embed(
            title="Thanks!",
            description="Thanks for voting for Nexus!",
            colour=self.bot.config.colours.neutral,
        )
        view = View()
        view.add_item(
            Button(
                style=ButtonStyle.gray,
                label="Top.gg",
                url=f"https://top.gg/bot/{self.bot.user.id}/vote",
            )
        )

        await ctx.reply(embed=embed, view=view, mention_author=False)


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
