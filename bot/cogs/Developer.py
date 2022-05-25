from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
from contextlib import suppress
from difflib import get_close_matches
from inspect import isasyncgen
from os import path
from pathlib import Path
from re import findall
from textwrap import indent
from traceback import format_exception
from typing import Callable, List, Tuple
import traceback as tb

import humanize
from discord.embeds import Embed
from discord.errors import NotFound
from discord.ext.commands import is_owner
from discord.ext.commands.core import bot_has_permissions
from discord.file import File
from discord.guild import Guild
from discord.member import Member
from import_expression import eval, exec
from utils import codeblocksafe
from utils.helpers import CodeblockConverter, paginatorinput
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import command
from utils.subclasses.context import NexusContext

COG_PATH = Path(path.dirname(__file__))


class Developer(Cog, hidden=True):
    """
    Commands for use only by the developer
    """

    def __init__(self, bot: Nexus):
        self.bot = bot
        self.COG_NAMES = "Jishaku"

    async def _evaluate_code(self, code: str, variables: dict):
        # sourcery skip: comprehension-to-generator, simplify-generator
        NEWLINE = "\n"

        formatted_code = []

        lines = code.splitlines()

        for index, line in enumerate(lines):
            if (
                index == len(lines) - 1
                and not line.strip().startswith("return")
                and not line.strip().startswith("yield")
            ):
                indent_num = len(line) - len(line.lstrip())

                if indent_num == 0:
                    line = f"return {line}"

            _line = line

            formatted_code.append(indent(_line, " " * 4))

        to_exec = f"""import discord\nfrom discord.ext import commands\n\nasync def func():\n{NEWLINE.join(formatted_code)}"""

        exec(to_exec, variables)

        result = eval("func()", variables)

        if isasyncgen(result):
            return "\n".join([str(i) async for i in result])

        return await result
    
    @is_owner()
    @command(name="sql")
    async def _sql(self, ctx: NexusContext, *, statement: str):
        try:
            if statement.lower().startswith("select"):
                return await ctx.embed(description=await self.bot.db.fetch(statement, one=not statement.lower().startswith("select *")))
            else:
                return await ctx.embed(description=await self.bot.db.execute(statement))
        except Exception as e:
            return await ctx.error("\n".join(tb.format_traceback(type(e), e, e.__traceback__)))
    
    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(name="eval", examples=["print('Hello world!')"])
    async def _eval(self, ctx: NexusContext, *, code: CodeblockConverter):
        """
        Evaluate python code

        Can only be used by the bot owner
        """

        variables = {
            "ctx": ctx,
            "author": ctx.author,
            "channel": ctx.channel,
            "bot": self.bot,
            "guild": ctx.guild,
            "message": ctx.message,
        }

        with suppress(NotFound):
            await ctx.message.add_reaction("▶")
        error = False
        try:
            result = await self._evaluate_code(
                code.code.replace("bot.http.token", '"[TOKEN]"'), variables
            )
        except Exception as e:
            result = e

        if result is None:
            embeds = []

        elif isinstance(result, Exception):
            error = True
            result = "".join(
                format_exception(type(result), result, result.__traceback__)
            ).replace(self.bot.http.token, "[TOKEN]")
            embeds = [
                f"```py\n{result[i : i + 2000]}```" for i in range(0, len(result), 2000)
            ]

        elif isinstance(result, (File, Embed, paginatorinput)):
            embeds = [result]

        else:
            result = codeblocksafe(str(result))
            embeds = [
                Embed(
                    description=f"```py\n{result[i:i + 4087]}```".replace(
                        self.bot.http.token, "[TOKEN]"
                    ),
                    colour=self.bot.config.colours.neutral,
                )
                for i in range(0, len(result), 4087)
            ]

        with suppress(NotFound):
            await ctx.message.add_reaction("✅" if not error else "\U00002757")

        if embeds:
            await ctx.paginate(embeds)

    async def _operate_on_cogs(
        self, cogs: str, func: Callable, options: List[str]
    ):
        if isinstance(cogs, str):
            cogs = [cogs]
        if not cogs:
            return await self._operate_on_cogs(self.bot.cogs, func, options)

        _cogs = []

        _to_load = []

        for cog in cogs:
            if isinstance(cog, tuple):
                cog = "".join(cog)

            if not cog.startswith("cogs.") and cog not in self.COG_NAMES:
                maybe_cogs = get_close_matches(cog, options)
                if not maybe_cogs:
                    _cogs.append(f"[ERROR] {cog} Couldn't find similar")
                    continue
                cog = maybe_cogs[0]
            _to_load.append(cog)

        for cog in _to_load:
            try:
                await func(cog)
                _cogs.append(f"[Success] {cog}")
            except Exception as e:
                _cogs.append(f"[ERROR] {cog}: {e}")

        return "\n".join(_cogs)

    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(
        name="load",
        examples=["cogs.Developer", "Jishaku", "cogs.Help cogs.Developer"],
    )
    async def _load(self, ctx: NexusContext, cogs: str):
        """
        Load the given cogs

        Can only be used by the bot owner
        """
        options = [
            "cogs."
            + str(file)
            .removeprefix(str(COG_PATH))
            .strip("\\")
            .strip("./")
            .removesuffix(".py")
            for file in COG_PATH.glob("./*.py")
        ]

        cogs = await self._operate_on_cogs(cogs, self.bot.load_extension, options)

        await ctx.paginate(
            Embed(
                description=f"```\n{cogs}```",
                colour=self.bot.config.colours.neutral,
            )
        )

    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(
        name="unload",
        examples=["cogs.Developer", "Jishaku", "Help cogs.Developer"],
    )
    async def _unload(self, ctx: NexusContext, cogs: str):
        """
        Unoad the given cogs

        Can only be used by the bot owner
        """
        options = [
            "cogs."
            + str(file)
            .removeprefix(str(COG_PATH))
            .strip("\\")
            .strip("./")
            .removesuffix(".py")
            for file in COG_PATH.glob("./*.py")
        ]

        cogs = await self._operate_on_cogs(cogs, self.bot.unload_extension, options)

        await ctx.paginate(
            Embed(
                description=f"```\n{cogs}```",
                colour=self.bot.config.colours.neutral,
            )
        )

    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(
        name="reload",
        examples=["cogs.Developer", "Jishaku", "Help cogs.Developer"],
    )
    async def _reload(self, ctx: NexusContext, cogs: str):
        """
        Reload the given cogs

        Can only be used by the bot owner
        """
        options = [
            "cogs."
            + str(file)
            .removeprefix(str(COG_PATH))
            .strip("\\")
            .strip("./")
            .removesuffix(".py")
            for file in COG_PATH.glob("./*.py")
        ]

        cogs = await self._operate_on_cogs(cogs, self.bot.reload_extension, options)

        await ctx.paginate(
            Embed(
                description=f"```\n{cogs}```",
                colour=self.bot.config.colours.neutral,
            )
        )

    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(name="as", examples=["@isaa_ctaylor#2494 help"])
    async def _as(self, ctx: NexusContext, user: Member, *, command: str):
        """
        Run the specified command as someone else

        Can only be used by the bot owner
        """

        context: NexusContext = await ctx.copy_with(
            author=user, content=ctx.prefix + command
        )

        if context.command is None:
            if context.invoked_with is None:
                return await ctx.send("Cannot run command as this user")
            return await ctx.send(f"Command {context.invoked_with} is not found")

        await context.command.invoke(context)

    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(name="sync", aliases=["pull"])
    async def _sync(self, ctx: NexusContext):
        """
        Sync with github.

        This command reloads any cogs that were changed.
        """
        async with ctx.typing():
            proc = await create_subprocess_shell("git pull", stdout=PIPE, stderr=PIPE)

            stdout, stderr = await proc.communicate()

            _ = ""

            if stdout:
                _ += f"[stdout]\n{stdout.decode()}"

            if stderr:
                _ += f"\n[stderr]\n{stderr.decode()}"

            _ = _ or "No output"

            _cogs = ""

            if cogs := findall(r"(?<=cogs\/)[^\/\W]*(?=\.py)", _):
                options = [
                    "cogs."
                    + str(file)
                    .removeprefix(str(COG_PATH))
                    .strip("\\")
                    .strip("./")
                    .removesuffix(".py")
                    for file in COG_PATH.glob("./*.py")
                ]

                _cogs = await self._operate_on_cogs(
                    cogs, self.bot.reload_extension, options
                )

        await ctx.paginate(
            Embed(
                description=f"```sh\n$ git pull\n{_}```"
                + (f"\n```\n{_cogs}```" if _cogs else ""),
                colour=self.bot.config.colours.neutral,
            )
        )

    @is_owner()
    @bot_has_permissions(send_messages=True, embed_links=True)
    @command(name="restart")
    async def _restart(self, ctx: NexusContext):
        """
        Restart the bot
        """
        with suppress(NotFound):
            await ctx.message.add_reaction("\U0001f44d")
        await self.bot.close()

    @is_owner()
    @command(name="sudo")
    async def _sudo(self, ctx: NexusContext, *, command: str):
        """
        Run a command bypassing all checks
        """
        _ctx: NexusContext = await ctx.copy_with(content=f"{ctx.prefix}{command}")

        await _ctx.command.reinvoke(_ctx)

    @Cog.listener(name="on_guild_join")
    async def _log_guild_joins(self, guild: Guild):
        embed = Embed(title="New guild!", colour=self.bot.config.colours.neutral)
        embed.add_field(name="Guild name", value=f"```\n{guild.name}```", inline=True)
        embed.add_field(
            name="Guild owner",
            value=f"```\n{guild.owner} - ({guild.owner.id})```",
            inline=True,
        )
        embed.add_field(
            name="Guild members", value=f"```\n{guild.member_count}```", inline=True
        )
        embed.add_field(
            name="Guild created",
            value=f"```\n{humanize.naturaldate(guild.created_at)}```",
            inline=True,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        await self.bot.get_channel(self.bot.config.channels.guilds).send(embed=embed)

    @Cog.listener(name="on_guild_remove")
    async def _log_guild_leaves(self, guild: Guild):
        if not guild.name:
            return
        embed = Embed(title="Guild loss!", colour=self.bot.config.colours.neutral)
        embed.add_field(
            name="Name",
            value=f"```\n{getattr(guild, 'name', 'Unavailable')}```",
            inline=True,
        )
        embed.add_field(
            name="Members lost",
            value=f"```\n{getattr(guild, 'member_count', 'Unavailable')}```",
            inline=True,
        )

        await self.bot.get_channel(self.bot.config.channels.guilds).send(embed=embed)


async def setup(bot: Nexus) -> None:
    await bot.add_cog(Developer(bot))
    await bot.tree.sync()
