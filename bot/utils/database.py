from time import sleep
import asyncpg
import asyncio
from dotenv import load_dotenv
from os import getenv


load_dotenv()

from . import Timer


class Database:
    def __init__(self, bot, **kwargs):
        self.bot = bot

    async def execute(self, command: str, *args):
        async with self.pool.acquire() as con:
            return await con.execute(command, *args)

    async def fetch(self, command: str, *args, one=True):
        if one:
                async with self.pool.acquire() as con:
                    return await con.fetchrow(command, *args)
        async with self.pool.acquire() as con:
            return await con.fetch(command, *args)

    @property
    async def ping(self):
        with Timer() as t:
            await self.fetch("SELECT 1")

            t.end()

            return t.elapsed
