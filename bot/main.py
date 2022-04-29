import asyncio
from os import getenv
import aiohttp

from dotenv import load_dotenv

from utils.subclasses.bot import Nexus

load_dotenv()

bot = Nexus()

async def main():
    async with bot:
        await bot.start(getenv("TOKEN"))
        
asyncio.run(main())
