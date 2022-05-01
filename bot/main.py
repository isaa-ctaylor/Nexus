import asyncio
from os import getenv

from dotenv import load_dotenv

from utils.subclasses.bot import Nexus

load_dotenv()

bot = Nexus()

async def main():
    async with bot:
        await bot.start(getenv("TOKEN"))

print("Starting now")
asyncio.run(main())
