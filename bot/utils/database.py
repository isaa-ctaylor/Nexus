import asyncpg
import asyncio

from asyncpg.connection import Connection


class Database:
    def __init__(self, **kwargs):
        self.pool = asyncio.get_event_loop().run_until_complete(
            self.new_connection(**kwargs)
        )

    async def new_connection(self, **kwargs):
        try:
            return await asyncpg.create_pool(
                user=kwargs.get("user", "Nexus"),
                password=kwargs.get("password", "nexus"),
                database=kwargs.get("database", "Nexus"),
                host=kwargs.get("host", "127.0.0.1"),
            )
        except asyncpg.exceptions.InvalidCatalogNameError:
            con: Connection = await asyncpg.connect(
                database="template1", user="postgres", password="postgres", host="127.0.0.1"
            )

            await con.execute("CREATE DATABASE Nexus OWNER postgres")

            await con.close()

            return self.new_connection(**kwargs)
