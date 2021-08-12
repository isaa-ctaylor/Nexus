from difflib import get_close_matches
from inspect import Parameter, isasyncgen
from os import path
from pathlib import Path
from textwrap import indent
from traceback import format_exception
from typing import Callable, List

from discord.embeds import Embed
from discord.ext.commands import command, is_owner
from discord.ext.commands.errors import MissingRequiredArgument
from discord.file import File
from discord.member import Member
from import_expression import eval, exec
from utils import codeblocksafe
from utils.helpers import CodeblockConverter, paginatorinput
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.context import NexusContext

COG_PATH = Path(path.dirname(__file__))


class Developer(Cog, hidden=True):
    """
    Commands for use only by the developer
    """

    def __init__(self, bot: Nexus):
        self.bot = bot
        self.COG_NAMES = ("Jishaku")

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
    @command(name="eval", cls=Command, examples=["print('Hello world!')"])
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

        await ctx.message.add_reaction("▶")
        error = False
        try:
            result = await self._evaluate_code(code.code.replace("bot.http.token", '"[TOKEN]"'), variables)
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
            result = codeblocksafe(repr(result))
            embeds = [
                Embed(
                    description=f"```py\n{result[i:i + 4087]}```".replace(
                        self.bot.http.token, "[TOKEN]"
                    ),
                    colour=self.bot.config.data.colours.neutral,
                )
                for i in range(0, len(result), 4087)
            ]

        await ctx.message.add_reaction("✅" if not error else "\U00002757")

        if embeds:
            await ctx.paginate(embeds)

    async def _operate_on_cogs(self, cogs: List[str], func: Callable, options: List[str]):
        if not cogs:
            raise MissingRequiredArgument(Parameter("cogs", Parameter.POSITIONAL_OR_KEYWORD))
        _cogs = []

        _to_load = []
        
        for cog in cogs:
            if not cog.startswith("cogs.") and cog not in self.COG_NAMES:
                maybe_cogs = get_close_matches(cog, options)
                if not maybe_cogs:
                    _cogs.append(f"[ERROR] {cog} Couldn't find similar")
                    continue
                cog = maybe_cogs[0]
            _to_load.append(cog)

        for cog in _to_load:
            try:
                func(cog)
                _cogs.append(f"[Success] {cog}")
            except Exception as e:
                _cogs.append(f"[ERROR] {cog}: {e}")

        return "\n".join(_cogs)

    @is_owner()
    @command(
        name="load",
        cls=Command,
        examples=["cogs.Developer", "Jishaku", "cogs.Help cogs.Developer"],
    )
    async def _load(self, ctx: NexusContext, *cogs: str):
        """
        Load the given cogs
        
        Can only be used by the bot owner
        """
        options = [
            "cogs."
            + str(file).removeprefix(str(COG_PATH)).strip("\\").removesuffix(".py")
            for file in COG_PATH.glob("./*.py")
        ]

        cogs = await self._operate_on_cogs(cogs, self.bot.load_extension, options)

        await ctx.paginate(
            Embed(
                description=f"```\n{cogs}```",
                colour=self.bot.config.data.colours.neutral,
            )
        )
        
    @is_owner()
    @command(
        name="unload",
        cls=Command,
        examples=["cogs.Developer", "Jishaku", "Help cogs.Developer"],
    )
    async def _unload(self, ctx: NexusContext, *cogs: str):
        """
        Unoad the given cogs
        
        Can only be used by the bot owner
        """
        options = [
            "cogs."
            + str(file).removeprefix(str(COG_PATH)).strip("\\").removesuffix(".py")
            for file in COG_PATH.glob("./*.py")
        ]

        cogs = await self._operate_on_cogs(cogs, self.bot.unload_extension, options)

        await ctx.paginate(
            Embed(
                description=f"```\n{cogs}```",
                colour=self.bot.config.data.colours.neutral,
            )
        )

    @is_owner()
    @command(
        name="reload",
        cls=Command,
        examples=["cogs.Developer", "Jishaku", "Help cogs.Developer"],
    )
    async def _reload(self, ctx: NexusContext, *cogs: str):
        """
        Reload the given cogs
        
        Can only be used by the bot owner
        """
        options = [
            "cogs."
            + str(file).removeprefix(str(COG_PATH)).strip("\\").removesuffix(".py")
            for file in COG_PATH.glob("./*.py")
        ]

        cogs = await self._operate_on_cogs(cogs, self.bot.reload_extension, options)

        await ctx.paginate(
            Embed(
                description=f"```\n{cogs}```",
                colour=self.bot.config.data.colours.neutral,
            )
        )

    @is_owner()
    @command(
        name="as",
        cls=Command,
        examples=["@isaa_ctaylor#2494 help"]
    )
    async def _as(self, ctx: NexusContext, user: Member, *, command: str):
        """
        Run the specified command as someone else
        
        Can only be used by the bot owner
        """
        
        context: NexusContext = await ctx.copy_with(author=user, content=ctx.prefix + command)
        
        if context.command is None:
            if context.invoked_with is None:
                return await ctx.send("Cannot run command as this user")
            return await ctx.send(f"Command {context.invoked_with} is not found")
        
        await context.command.invoke(context)

def setup(bot: Nexus) -> None:
    bot.add_cog(Developer(bot))
