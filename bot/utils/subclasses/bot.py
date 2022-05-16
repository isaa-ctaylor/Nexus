import re
from wsgiref.util import application_uri
import wavelink
from logging import INFO, getLogger
from time import sleep
from traceback import format_exception
from os import getenv

from aiohttp import ClientSession
import asyncpg
from discord import Message
from discord.ext.commands import Bot, CheckFailure
from discord.ext.commands.bot import when_mentioned_or
from discord.flags import Intents

from ..config import CONFIG
from ..database import Database
from .context import NexusContext

_intents = Intents.all()
_intents.members = True
_intents.presences = False


def get_prefix(bot, message: Message):
    if not isinstance(message, Message):
        return when_mentioned_or("/")(bot, message)

    if hasattr(bot, "prefixes"):
        prefixes = bot.prefixes.get(message.guild.id, ["nxs"])
    else:
        prefixes = ["nxs"]

    prefix = prefixes[0]

    comp = re.compile("^(" + "|".join(map(re.escape, [prefix])) + ").*", flags=re.I)
    match = comp.match(message.content)
    if match is not None:
        return when_mentioned_or(match[1])(bot, message)
    return when_mentioned_or("nxs")(bot, message)


class Nexus(Bot):
    def __init__(self, intents: Intents = None, *args, **kwargs):
        self.wavelink: wavelink.Node = None
        self.config = CONFIG

        kwargs["command_prefix"] = get_prefix
        kwargs["case_insensitive"] = kwargs.pop("case_insensitive", True)
        kwargs["slash_commands"] = kwargs.pop("slash_commands", True)
        
        kwargs["application_id"] = 869487103703138364

        super().__init__(intents=intents or _intents, *args, **kwargs)

        self.owner_id = self.config.owner
        self.strip_after_prefix = True

        # self.logger = getLogger("discord")
        # self.logger.setLevel(INFO)
        # self.logger.addHandler(
        #     WebhookHandler(
        #         level=INFO, bot=self, url=getenv("LOGGING"), session=self.session
        #     )
        # )
        
    async def setup_hook(self) -> None:

        self.session = ClientSession()

        self.database = self.db = Database(self)

        user, password, database, host = (
            "postgres",
            getenv("DATABASE"),
            "nexus",
            "localhost"
        )

        self.db.pool = await asyncpg.create_pool(
            user=user, password=password, database=database, host=host
        )

        self.add_check(self._check_cog_not_blacklisted)

        await self.db.execute(
            r"""CREATE TABLE IF NOT EXISTS prefixes     (guild_id BIGINT NOT NULL, prefixes TEXT[] DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS automod      (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');
                CREATE TABLE IF NOT EXISTS spamchecker  (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');
                CREATE TABLE IF NOT EXISTS modlogs      (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false', channel TEXT);
                CREATE TABLE IF NOT EXISTS chatlimit    (guild_id BIGINT NOT NULL, channel_id BIGINT NOT NULL, num INT NOT NULL);
                CREATE TABLE IF NOT EXISTS welcome      (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false', channel BIGINT, message TEXT NOT NULL, role BIGINT);
                CREATE TABLE IF NOT EXISTS reminders    (reminder_id SERIAL, owner_id BIGINT NOT NULL, channel_id BIGINT NOT NULL, timeend BIGINT NOT NULL, timestart BIGINT NOT NULL, reason TEXT NOT NULL, message_id BIGINT NOT NULL);
                CREATE TABLE IF NOT EXISTS dailyreminders    (reminder_id SERIAL, owner_id BIGINT NOT NULL, channel_id BIGINT NOT NULL, hour INT, minute INT, second INT, reason TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cogblacklist (guild_id BIGINT NOT NULL, blacklist TEXT[] DEFAULT '{}')
            """
        )


        self.prefixes = {
            r["guild_id"]: r["prefixes"]
            for r in [
                dict(r)
                for r in await self.db.fetch("SELECT * FROM prefixes", one=False)
            ]
        }

        if cogs := self.config.cogs:
            for cog in cogs:
                try:
                    await self.load_extension(cog)
                except Exception as e:
                    print("".join(format_exception(type(e), e, e.__traceback__)))

    async def _check_cog_not_blacklisted(self, ctx: NexusContext) -> bool:
        if ctx.author.id == self.owner_id:
            return True
        if ctx.author.id == ctx.guild.owner_id:
            return True

        if ctx.command.cog_name in [
            cog.qualified_name
            for cog in self.cogs.values()
            if cog.hidden or cog.qualified_name in ["Settings"]
        ]:
            return True
        data = await self.db.fetch(
            "SELECT blacklist FROM cogblacklist WHERE guild_id = $1", ctx.guild.id
        )
        if data is None:
            return True

        if ctx.command.cog_name.capitalize().strip() in data["blacklist"]:
            raise CheckFailure(f"The {ctx.command.cog_name} module is disabled!")

        return True

    async def on_ready(self):
        print(f"Logged in as {self.user} - {self.user.id}")

    async def close(self):

        if self.session:
            await self.session.close()

        await super().close()

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or NexusContext)
