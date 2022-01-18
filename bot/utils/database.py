import asyncpg
import asyncio
from dotenv import load_dotenv
from os import getenv


load_dotenv()

from . import Timer


class Database:
    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.pool = asyncio.get_event_loop().run_until_complete(
            self.new_connection(**kwargs)
        )

    async def new_connection(self, **kwargs):
        user, password, database, host = (
            kwargs.get("user", "postgres"),
            kwargs.get("password", getenv("DATABASE")),
            kwargs.get("database", "nexus"),
            kwargs.get("host", "localhost"),
        )

        self.bot.logger.info(
            f"Creating database connection with params user={user}, password={password}, database={database}, host={host}."
        )

        pool = await asyncpg.create_pool(
            user=user, password=password, database=database, host=host
        )

        self.bot.logger.info("Database pool created.")

        return pool

    async def execute(self, command: str, *args):
        return await self.pool.execute(command, *args)

    async def fetch(self, command: str, *args, one=True):
        if one:
            return await self.pool.fetchrow(command, *args)
        return await self.pool.fetch(command, *args)

    @property
    async def ping(self):
        with Timer() as t:
            await self.fetch("SELECT 1")

            t.end()

            return t.elapsed
