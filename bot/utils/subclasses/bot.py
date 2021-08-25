from ..helpers import get_prefix
from logging import INFO, getLogger
from traceback import format_exception
from os import getenv

from aiohttp import ClientSession
from discord.ext.commands import Bot
from dotenv import load_dotenv

from ..config import Config
from ..logging import WebhookHandler
from .context import NexusContext
from ..database import Database

from discord.ext.commands.core import _CaseInsensitiveDict

load_dotenv()


class Nexus(Bot):
    def __init__(self, *args, **kwargs):
        self.config = Config()

        kwargs["command_prefix"] = kwargs.pop("command_prefix", get_prefix)
        kwargs["case_insensitive"] = kwargs.pop("case_insensitive", True)

        cogs = self.config.data.cogs

        super().__init__(*args, **kwargs)

        self.owner_id = self.config.data.owner
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
                CREATE TABLE IF NOT EXISTS spamchecker (guild_id BIGINT NOT NULL, enabled BOOL DEFAULT 'false');"""
            )
        )
        
        self.loop.create_task(self.__ainit__())
        
    async def __ainit__(self):
        self.session = ClientSession()

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
