from logging import INFO, getLogger
from traceback import format_exception
from os import getenv

from aiohttp import ClientSession
from discord.ext.commands import Bot
from dotenv import load_dotenv

from ..config import Config
from ..logging import WebhookHandler
from .context import NexusContext

load_dotenv()


class Nexus(Bot):
    def __init__(self, *args, **kwargs):
        self.session: ClientSession = kwargs.pop("session", ClientSession())

        self.config = Config()

        cogs = self.config.data.cogs

        super().__init__(*args, **kwargs)

        self.owner_id = self.config.data.owner
        self.strip_after_prefix = True
        self.case_insensitive = True
        
        logger = getLogger("discord")
        logger.setLevel(INFO)
        logger.addHandler(WebhookHandler(level=INFO, bot=self, url=getenv("LOGGING"), session=self.session))

        if cogs:
            for cog in cogs:
                try:
                    self.load_extension(cog)
                except Exception as e:
                    print(
                        "".join(
                            format_exception(type(e), e, e.__traceback__)
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

        super().run(TOKEN)
