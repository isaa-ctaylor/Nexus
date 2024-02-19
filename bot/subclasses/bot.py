import logging
import os
import typing

import aiohttp
import asyncpg
import discord
import wavelink
import yaml
from discord.app_commands import CommandTree
from discord.ext import commands
from discord.ext.commands import Bot
from dotenv import load_dotenv

load_dotenv()

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"

with open("config.yaml", "r") as f:
    CONFIG: typing.Dict[str, typing.Union[str, dict, list, bool]] = yaml.safe_load(f)


intents = discord.Intents.default()
intents.message_content = True


class Bot(Bot):
    def __init__(self, *args, **kwargs):
        kwargs["command_prefix"] = kwargs.get("command_prefix", commands.when_mentioned)
        kwargs["intents"] = kwargs.get("intents", intents)
        kwargs["tree_cls"] = kwargs.get("tree_cls", CommandTree)
        # kwargs["help_command"] = kwargs.get("help_command", None)
        discord.utils.setup_logging()
        super().__init__(*args, **kwargs)

        self.config = CONFIG

        self.session: typing.Optional[aiohttp.ClientSession] = kwargs.get(
            "session", None
        )

        self.voice_extras: typing.Dict[int, typing.Dict[str, discord.Message]] = {}

        self.logger = logging.getLogger("discord.bot")
        self.logger.info("#############################")
        self.logger.info(f"Running on discord.py {discord.__version__}")
        self.logger.info("#############################")

        self.database: asyncpg.Connection

    async def setup_hook(self):
        if database := self.config.get("database", None):
            self.database = await asyncpg.connect(
                host=database.get("host", None),
                port=database.get("port", 5432),
                user=database.get("user", None),
                database=database.get("database", None),
                password=os.getenv("DATABASE"),
            )
            self.logger.getChild("database").info("Database connected")

        for plugin in self.config.get("plugins", []):
            logger = self.logger.getChild("plugins")
            logger.info(f"Initialising {plugin}")
            await self.load_extension(plugin)

        if WL_CONF := self.config.get("wavelink", None):
            wl_logger = logging.getLogger("discord.wavelink")

            host: str = WL_CONF.get("host", None)
            port = WL_CONF.get("port", 2333)
            secure = WL_CONF.get("secure", True)
            password = WL_CONF.get("password", os.getenv("WAVELINK"))

            if host is None:
                wl_logger.critical(
                    "URL not provided, cannot initialise wavelink nodes!"
                )
            else:
                nodes = [
                    wavelink.Node(
                        uri=f"http{'s' if secure else ''}://{host}:{port}",
                        password=password,
                        session=self.session,
                    )
                ]

                try:
                    n = await wavelink.Pool.connect(nodes=nodes, client=self)
                    wl_logger.info(
                        f"Connected {len(n)}/{len(nodes)} wavelink node{'s' if len(n) > 1 else ''}"
                    )
                except wavelink.AuthorizationFailedException:
                    wl_logger.critical(
                        "Wavelink password incorrect. Cannot connect nodes!"
                    )
                except wavelink.NodeException:
                    wl_logger.critical(
                        "Wavelink node(s) failed to connect. Please check wavelink version"
                    )

        # Sync all commands to development guild
        if debug := self.config.get("debug", False):
            self.logger.info("DEBUG mode is ON")
            if debug.get("sync", False):
                guild = self.config.get("dev", {}).get("guild")
                if guild:
                    self.logger.info("Syncing to development guild")
                    guild = discord.Object(guild)
                    self.tree.clear_commands(guild=guild)
                    self.tree.copy_global_to(guild=guild)
                    await self.tree.sync(guild=guild)
                else:
                    self.logger.warn(
                        "'guild' is not specified in config.yaml, could not sync to development server!"
                    )

    async def db_get_user(self, user_id: int) -> dict:
        d = await self.database.fetchrow(
            "SELECT * FROM public.user WHERE id = $1", user_id
        )

        if d:
            return dict(d)

    async def db_create_user(self, user_id: int) -> None:
        await self.database.execute("INSERT INTO public.user VALUES ($1)", user_id)

    async def ensure_user(self, user_id: int) -> None:
        user = await self.db_get_user(user_id)
        if not user:
            await self.db_create_user(user_id)
