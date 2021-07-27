from ..config import Config
from aiohttp import ClientSession
from discord.ext.commands import Bot


class Nexus(Bot):
    def __init__(self, *args, **kwargs):
        self.session: ClientSession = kwargs.pop("session", ClientSession())

        self.config = Config()

        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f"Logged in as {self.user} - {self.user.id}")
    
    async def close(self):
        if self.session:
            await self.session.close()

        await super().close()
