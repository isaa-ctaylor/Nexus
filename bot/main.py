import asyncio
import os

import aiohttp
import sentry_sdk
from dotenv import load_dotenv
from subclasses.bot import Bot
import contextlib

load_dotenv()


sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
    environment="bot-dev",
)

with contextlib.suppress(KeyboardInterrupt):

    async def main():
        async with aiohttp.ClientSession() as session:
            async with Bot(session=session) as bot:
                await bot.start(os.getenv("TOKEN"))

    asyncio.run(main())
