from discord.ext.commands.bot import when_mentioned_or, _FakeSlashMessage
from discord.ext.commands.core import _CaseInsensitiveDict
from discord.flags import Intents
from logging import INFO, getLogger
from traceback import format_exception
from os import getenv

from aiohttp import ClientSession
from discord.ext.commands import Bot
from dotenv import load_dotenv

from ..config import CONFIG
from ..logging import WebhookHandler
from .context import NexusContext
from ..database import Database

import re

load_dotenv()


_intents = Intents.all()
_intents.members = True
_intents.presences = False


def get_prefix(bot, message):
    if isinstance(message, _FakeSlashMessage):
        return when_mentioned_or("/")(bot, message)

    if hasattr(bot, "prefixes"):
        prefixes = bot.prefixes.get(message.guild.id, ["nxs"])
    else:
        prefixes = ["nxs"]

    prefix = prefixes[0]

    comp = re.compile("^(" + "|".join(map(re.escape, [prefix])) + ").*", flags=re.I)
    match = comp.match(message.content)
    if match is not None:
        return when_mentioned_or(match.group(1))(bot, message)
    return when_mentioned_or("nxs")(bot, message)


class Nexus(Bot):
    def __init__(self, intents: Intents = None, *args, **kwargs):
        self._BotBase__cogs = _CaseInsensitiveDict()

        self.session: ClientSession = kwargs.pop("session", ClientSession())

        self.config = CONFIG

        kwargs["command_prefix"] = get_prefix
        kwargs["case_insensitive"] = kwargs.pop("case_insensitive", True)
        kwargs["slash_commands"] = kwargs.pop("slash_commands", True)

        cogs = self.config.cogs

        super().__init__(intents=intents or _intents, *args, **kwargs)

        self.owner_id = self.config.owner
        self.strip_after_prefix = True

        self.logger = getLogger("discord")
        self.logger.setLevel(INFO)
        self.logger.addHandler(
            WebhookHandler(
                level=INFO, bot=self, url=getenv("LOGGING"), session=self.session
            )
        )
        self.database = self.db = Database(self)

        if cogs:
            for cog in cogs:
                try:
                    self.load_extension(cog)
                except Exception as e:
                    print("".join(format_exception(type(e), e, e.__traceback__)))

        self.loop.create_task(self.__ainit__())

    async def __ainit__(self):
        await self.db.execute(
            r"""CREATE TABLE IF NOT EXISTS prefixes     (guild_id BIGINT NOT NULL, prefixes TEXT[] DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS automod      (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');
                CREATE TABLE IF NOT EXISTS spamchecker  (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');
                CREATE TABLE IF NOT EXISTS modlogs      (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false', channel BIGINT);
                CREATE TABLE IF NOT EXISTS chatlimit    (guild_id BIGINT NOT NULL, channel_id BIGINT NOT NULL, num INT NOT NULL);"""
        )

        self.prefixes = {
            r["guild_id"]: r["prefixes"]
            for r in [
                dict(r)
                for r in await self.db.fetch("SELECT * FROM prefixes", one=False)
            ]
        }

    async def on_ready(self):
        print(f"Logged in as {self.user} - {self.user.id}")

    async def close(self):

        if self.session:
            await self.session.close()

        await super().close()

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=cls or NexusContext)

    def run(self, *args, **kwargs):
        TOKEN = getenv("TOKEN")

        super().run(TOKEN, *args, **kwargs)
