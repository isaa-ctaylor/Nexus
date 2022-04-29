import asyncio
from os import getenv
import aiohttp

from dotenv import load_dotenv

from utils.subclasses.bot import Nexus

load_dotenv()
print("a")
bot = Nexus()
print("b")
async def main():
    print("c")
    async with bot:
        print("d")
        await bot.start(getenv("TOKEN"))

print("Starting now")
asyncio.run(main())
