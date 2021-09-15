from discord.flags import Intents
from ..helpers import get_prefix
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

from discord.ext.commands.core import _CaseInsensitiveDict

load_dotenv()


_intents = Intents.all()
_intents.members = True
_intents.presences = False


class Nexus(Bot):
    def __init__(self, intents: Intents = None, *args, **kwargs):
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

        self._BotBase__cogs = _CaseInsensitiveDict()

        if cogs:
            for cog in cogs:
                try:
                    self.load_extension(cog)
                except Exception as e:
                    print("".join(format_exception(type(e), e, e.__traceback__)))

        self.database = Database(self)
        self.db = self.database

        self.loop.create_task(
            self.db.execute(
                r"""CREATE TABLE IF NOT EXISTS prefixes (guild_id BIGINT NOT NULL, prefixes TEXT[] DEFAULT '{}');
                CREATE TABLE IF NOT EXISTS automod (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');
                CREATE TABLE IF NOT EXISTS spamchecker (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');
                CREATE TABLE IF NOT EXISTS modlogs (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false', channel BIGINT);"""
            )
        )

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
