from asyncio import create_task
from asyncio.events import get_running_loop
from contextlib import suppress
from logging import Formatter, Handler, LogRecord

from aiohttp import ClientSession
from discord import Webhook
from discord.embeds import Embed
from discord.webhook.sync import SyncWebhook

from . import codeblocksafe


class WebhookHandler(Handler):
    def __init__(self, *, level, bot, url: str, session: ClientSession, format: str = "%(asctime)s:%(levelname)s:%(name)s: %(message)s"):
        self.level = level
        self.url = url
        self.formatter = Formatter(format)
        self.async_webhook = Webhook.from_url(self.url, session=session)
        self.sync_webhook = SyncWebhook.from_url(self.url)
        self.bot = bot
        
    def handle(self, log: LogRecord) -> str:
        loop = None

        with suppress(RuntimeError):
            loop = get_running_loop()

        with suppress(Exception):
            if loop is not None:
                create_task(self._async_handle(log))
            else:
                self._sync_handle(log)

        return log
    
    async def _async_handle(self, log: LogRecord):
        return await self.async_webhook.send(embed=Embed(description=f"```json\n{codeblocksafe(self.formatter.format(log).replace(self.bot.http.token, '[TOKEN]'))}```", colour=16711774))

    def _sync_handle(self, log: LogRecord):
        return self.sync_webhook.send(embed=Embed(description=f"```json\n{codeblocksafe(self.formatter.format(log).replace(self.bot.http.token, '[TOKEN]'))}```", colour=16711774))
