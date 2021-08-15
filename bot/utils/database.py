import asyncpg
import asyncio

from asyncpg.connection import Connection


class Database:
    def __init__(self, **kwargs):
        self.pool = asyncio.get_event_loop().run_until_complete(
            self.new_connection(**kwargs)
        )

    async def new_connection(self, **kwargs):
        return await asyncpg.create_pool(
            user=kwargs.get("user", "postgres"),
            password=kwargs.get("password", "postgres"),
            database=kwargs.get("database", "nexus"),
            host=kwargs.get("host", "localhost"),
        )
