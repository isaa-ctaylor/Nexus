from io import BytesIO
from math import floor, log10
from os import getenv
from typing import Any, List, Optional
from discord.channel import TextChannel
from discord.member import Member

from idevision.errors import InvalidRtfmLibrary
import parsedatetime
from utils import hyperlink
from utils.scraper import Website

import pytesseract
from aiohttp import InvalidURL
from async_timeout import timeout
from discord import ButtonStyle
from discord.embeds import Embed
from discord.ext import tasks
from discord.ext.commands import Converter
from discord.ext.commands.converter import UserConverter
from discord.ext.commands.errors import BadArgument, CommandError
from discord.ui import Button, View
from dotenv.main import load_dotenv
from idevision import async_client
from PIL import Image, ImageOps, UnidentifiedImageError
from utils import Timer, codeblocksafe, executor
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import command, group
from utils.subclasses.context import NexusContext
import re
from utils.scraper import Search
from parsedatetime import Calendar
import datetime
from dateutil.relativedelta import relativedelta
import asyncio
import humanize


load_dotenv()


SIMPLETIME = re.compile(
    """(?:(?P<years>[0-9])(?:years?|y))?
       (?:(?P<months>[0-9]{1,2})(?:months?|mo))?
       (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?
       (?:(?P<days>[0-9]{1,5})(?:days?|d))?
       (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?
       (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?
       (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?
    """,
    re.VERBOSE,
)


class TimeInPast(Exception):
    pass


class InvalidTimeProvided(CommandError):
    pass


class TimeConverter(Converter):
    async def convert(self, ctx: NexusContext, argument):
        date_obj = ctx.message.created_at

        remaining = argument
        match = SIMPLETIME.match(remaining)
        if match is not None and match.group(0):
            while match is not None and match.group(0):
                data = {k: int(v) for k, v in match.groupdict(default=0).items()}
                remaining = str(remaining[match.end() :]).strip()
                date_obj += relativedelta(**data)

                match = SIMPLETIME.match(remaining)
            result_dt = date_obj

        else:
            remaining = self._check_startswith(argument)

            times = Calendar(version=parsedatetime.VERSION_CONTEXT_STYLE).nlp(
                remaining, sourceTime=date_obj
            )
            if times is None or len(times) == 0:
                raise InvalidTimeProvided("Invalid time provided!")

            dt, timestatus, beginning, end, _ = times[0]

            if not timestatus.hasDateOrTime:
                raise InvalidTimeProvided("Invalid time provided!")

            if beginning not in (0, 1) and end != len(argument):
                raise InvalidTimeProvided(
                    "I see a time, but it is not at the start or end of your input! (or I didn't understand you)"
                )

            if not timestatus.hasTime:
                dt = dt.replace(
                    hour=date_obj.hour,
                    minute=date_obj.minute,
                    second=date_obj.second,
                    microsecond=date_obj.microsecond,
                )

            if timestatus.accuracy == parsedatetime.pdtContext.ACU_HALFDAY:
                dt = dt.replace(day=date_obj.day + 1)

            result_dt = dt.replace(tzinfo=datetime.timezone.utc)

            if beginning in (0, 1):
                if beginning == 1:
                    if remaining[0] != '"':
                        raise InvalidTimeProvided("Expected quote before time input...")

                    if end >= len(argument) or remaining[end] != '"':
                        raise InvalidTimeProvided(
                            "If the time is quoted, you must unquote it."
                        )

                    remaining = remaining[end + 1 :].lstrip(" ,.!")
                else:
                    remaining = remaining[end:].lstrip(" ,.!")
            elif len(argument) == end:
                remaining = remaining[:beginning].strip()

        return self._run_checks(ctx.message.created_at, result_dt, remaining)

    def _check_startswith(self, reason: str):
        if reason.startswith("me") and reason[:6] in (
            "me to ",
            "me in ",
            "me at ",
        ):
            reason = reason[6:]

        if reason[:2] == "me" and reason[:9] == "me after ":
            reason = reason[9:]

        if reason[:3] == "me ":
            reason = reason[3:]

        if reason[:2] == "me":
            reason = reason[2:]

        if reason[:6] == "after ":
            reason = reason[6:]

        if reason[:5] == "after":
            reason = reason[5:]

        if reason.endswith("from now"):
            reason = reason[:-8]

        return reason.strip()

    def _run_checks(self, now, dt, remaining):
        if dt < now:
            raise InvalidTimeProvided("Time is in the past!")

        if not remaining:
            remaining = "..."

        if remaining.startswith("to "):
            remaining = remaining.removeprefix("to ")

        elif remaining.startswith("to"):
            remaining = remaining.removeprefix("to")

        return dt, remaining


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


DESTINATIONS = {
    "dpy": "https://discordpy.readthedocs.io/en/stable",
    "dpy2": "https://discordpy.readthedocs.io/en/master",
    "edpy": "https://enhanced-dpy.readthedocs.io/en/latest",
    "py": "https://docs.python.org/3",
    "py2": "https://docs.python.org/2",
}
URL_REGEX = (
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


class IdevisionLocation(Converter):
    async def convert(self, ctx: NexusContext, arg: Any):
        if arg.lower() == "list":
            return arg

        if arg.lower() in ["discord.py", "discordpy"]:
            arg = "dpy"

        if arg.lower() in [
            "discord.py2",
            "discord.py-2",
            "discordpy2",
            "discordpy-2",
            "dpy-2",
        ]:
            arg = "dpy2"

        if arg.lower() in ["enhanced-discord.py", "enhanced-discordpy"]:
            arg = "edpy"

        if arg.lower() in ["python", "python3", "py3"]:
            arg = "py"

        if arg.lower() in ["python2"]:
            arg = "py2"

        if arg in DESTINATIONS:
            return arg

        if re.match(URL_REGEX, arg) is not None:
            return arg

        raise BadArgument(f"{arg} is not a valid rtfm location!")


class Utility(Cog):
    """
    Useful commands
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

        self.rtfm_destinations = DESTINATIONS
        self.idevision = async_client(getenv("IDEVISION"))

        self._send_reminders.start()

    @command(
        name="redirectcheck",
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

    @command(name="ping")
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

    @command(name="ocr")
    async def _ocr(self, ctx: NexusContext, *, image: str = None):
        """
        Read text from an image

        If just supplying the image does not work, or the image is light text on a dark background, try adding "--invert" to the end of your message
        """
        invert = False
        if image and "--invert" in image:
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
            if (ref := ctx.message.reference) and (
                attachments := ref.resolved.attachments
            ):
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

    @command(name="vote")
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

    @command(name="rtfm")
    async def _rtfm(
        self,
        ctx: NexusContext,
        location: Optional[IdevisionLocation] = "py",
        *,
        query: str = None,
    ):
        """
        Search through sphinx documentation

        If you don't know what this is, then you probably don't need it!
        """
        if not query:
            if location.lower() == "list":
                return await ctx.embed(
                    description="\n".join(
                        f"{k}: {v}" for k, v in self.rtfm_destinations.items()
                    )
                )
            if re.match(URL_REGEX, location):
                return await ctx.paginate(location)
            if location in self.rtfm_destinations:
                return await ctx.paginate(self.rtfm_destinations[location])
            return await ctx.error(f"{location} is not a valid rtfm location!")

        try:
            data = await self.idevision.sphinxrtfm(
                self.rtfm_destinations.get(location, location), query
            )
        except InvalidRtfmLibrary as e:
            return await ctx.error(str(e))

        if not data.nodes:
            return await ctx.error("Nothing found!")

        return await ctx.embed(
            description="\n".join(f"[`{k}`]({v})" for k, v in data.nodes.items())
        )

    @command(name="google")
    async def _google(self, ctx: NexusContext, *, query: str):
        """
        Search something on google
        """
        s = Search()
        data = await s.search(query)

        if not data.websites:
            return await ctx.error(f"No results for {codeblocksafe(query)}!")

        if isinstance(data.websites, Exception):
            raise data.websites

        embeds = [
            Embed(
                title=f"Search results for {query}",
                colour=self.bot.config.colours.neutral,
            )
        ]

        _description = []
        wc = 5  # Website count to add to first page

        if snippet := data.snippet:
            wc = 2
            if title := snippet.title:
                _description.append(f"**{title}**")
            if description := snippet.description:
                _description.append(description)
            if link := snippet.link:
                _description.append(hyperlink(link.text, link.href))

        if _description:
            embeds[0].description = "\n".join(_description)

        paginated_websites: List[List[Website]] = [data.websites[:wc]] + [
            data.websites[wc:][i : i + 5] for i in range(0, len(data.websites[wc:]), 5)
        ]

        for i, page in enumerate(paginated_websites):
            try:
                embeds[i]
            except IndexError:
                embeds.append(Embed(colour=self.bot.config.colours.neutral))

            websites = []
            for website in page:
                _ = []
                if title := website.title:
                    _.append(hyperlink(f"**{title}**", website.href))
                if description := website.description:
                    _.append(description)
                websites.append("\n".join(_))

            if embeds[i].description:
                embeds[i].description += "\n\n" + "\n\n".join(websites)
            else:
                embeds[i].description = "\n\n".join(websites)

        await ctx.paginate(embeds)

    @group(
        name="remind",
        usage="<when> [what]",
        examples=["me in 1h to do the dishes", "me in four hours eat some cake"],
        invoke_without_command=True,
    )
    async def _remind(self, ctx: NexusContext, *, dateandtime: TimeConverter):
        """
        Remind you to do something

        Time input can be in "short format" (e.g. 1h 2m) or natural speech (e.g. "in two hours") and must be at the start or end of your input"""
        if not ctx.invoked_subcommand:
            await self._create_timer(
                ctx, ctx.author, ctx.channel, dateandtime[0], dateandtime[1]
            )

    @_remind.error
    async def _remind_error(self, ctx: NexusContext, error: Exception):
        if isinstance(error, InvalidTimeProvided):
            return await ctx.error(str(error))
        raise error

    async def _create_timer(
        self,
        ctx: NexusContext,
        owner: Member,
        channel: TextChannel,
        when: datetime.datetime,
        reason: str,
    ):
        if (when - ctx.message.created_at).total_seconds() <= 60:
            self.bot.loop.create_task(
                self._send_timer(
                    ctx.message.created_at,
                    owner.id,
                    channel.id,
                    when.timestamp(),
                    ctx.message.created_at.timestamp(),
                    reason,
                    ctx.message.id,
                )
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO reminders (owner_id, channel_id, timeend, timestart, reason, message_id) VALUES ($1, $2, $3, $4, $5, $6)",
                owner.id,
                channel.id,
                int(when.timestamp()),
                int(ctx.message.created_at.timestamp()),
                str(reason),
                ctx.message.id,
            )

        await ctx.reply(
            f"Alright {ctx.author.mention}, <t:{int(when.timestamp())}:R>: {reason}"
        )

    async def _send_timer(
        self,
        now: datetime.datetime,
        owner: int,
        channel: int,
        end: float,
        start: float,
        reason: str,
        message: int,
    ):
        sleep = end - now.timestamp()
        print(sleep)
        await asyncio.sleep(sleep)
        channel = self.bot.get_channel(channel) or self.bot.fetch_channel(channel)
        message = await channel.fetch_message(message) if channel else None
        await channel.send(
            f"<@{owner}>, <t:{int(start)}:R>: {reason}\n\n{message.jump_url if message else ''}"
        )

    @tasks.loop(minutes=1)
    async def _send_reminders(self):
        now = datetime.datetime.utcnow()
        data = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE (timeend - $1) <= 60",
            int(now.timestamp()),
            one=False,
        )

        if not data:
            return

        for datum in data:
            self.bot.loop.create_task(
                self._send_timer(
                    now,
                    datum["owner_id"],
                    datum["channel_id"],
                    datum["timeend"],
                    datum["timestart"],
                    datum["reason"],
                    datum["message_id"],
                )
            )

        await self.bot.db.execute(
            "DELETE FROM reminders WHERE (timeend - $1) <= 60",
            int(now.timestamp()),
        )

    @_remind.command(name="remove", usage="<id>")
    async def _remind_remove(self, ctx: NexusContext, index: int):
        """
        Remove a set reminder given its id
        """
        data = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE owner_id = $1", ctx.author.id, one=False
        )

        if not data:
            return await ctx.error("No reminders set!")

        if index not in [r["reminder_id"] for r in data]:
            return await ctx.error("No reminder with that ID found!")

        await self.bot.db.execute(
            "DELETE FROM reminders WHERE (owner_id = $1 and reminder_id = $2)",
            ctx.author.id,
            index,
        )

        await ctx.message.add_reaction("👍")

    @_remind.command(name="list")
    async def _remind_list(self, ctx: NexusContext):
        """
        List all your current reminders
        """
        data = sorted(
            await self.bot.db.fetch(
                "SELECT * FROM reminders WHERE owner_id = $1", ctx.author.id, one=False
            ),
            key=lambda x: x["timeend"],
        )

        if not data:
            return await ctx.error("No currently set reminders!")

        pages = [data[i : i + 5] for i in range(0, len(data), 5)]

        embeds = [
            Embed(
                title="Reminders",
                colour=self.bot.config.colours.neutral,
                description="\n".join(
                    f"ID: {r['reminder_id']} <t:{int(r['timeend'])}:R>:\n{r['reason']}"
                    for r in page
                ),
            ).set_footer(text=f"{len(data)} reminder{'s' if len(data) > 1 else ''}")
            for page in pages
        ]

        await ctx.paginate(embeds)


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
