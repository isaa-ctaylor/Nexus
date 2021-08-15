import asyncpg
import asyncio

from asyncpg.connection import Connection


class Database:
    def __init__(self, bot, **kwargs):
        self.bot = bot
        self.pool = asyncio.get_event_loop().run_until_complete(
            self.new_connection(**kwargs)
        )

    async def new_connection(self, **kwargs):
        user, password, database, host = (
            kwargs.get("user", "postgres"),
            kwargs.get("password", "postgres"),
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