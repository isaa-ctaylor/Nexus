from contextlib import suppress
from utils.subclasses.context import NexusContext
from typing import List, Mapping, Optional, Union

from discord import Embed, File
from discord.abc import Messageable
from discord.ext.commands.core import bot_has_permissions, command
from discord.ext.commands.help import HelpCommand, _HelpCommandImpl
from discord.ui import View
from utils.helpers import paginatorinput
from utils import naturallist
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command, Group
from .Utility import LinkView

PER_PAGE = 10


async def _show(
    ctx: NexusContext, item: Optional[Union[Cog, Command, Group, _HelpCommandImpl]]
):
    if isinstance(item, (Command, Group, _HelpCommandImpl)):
        item = item.cog

    if not list(item.walk_commands()):
        return False

    if ctx.author.id == ctx.bot.owner_id or ctx.author.id in ctx.bot.owner_ids:
        return True

    return not item.hidden


class NexusHelp(HelpCommand):
    def __init__(self, *args, **kwargs):
        self.examples = []

        super().__init__(*args, **kwargs)

    def get_command_signature(self, c: Command):
        return f"{self.context.clean_prefix}{c.qualified_name} {c.signature}"

    async def _send(
        self,
        items: Union[list, Embed, paginatorinput],
        *,
        destination: Optional[Messageable] = None,
        view: View = None,
        **kwargs,
    ) -> None:
        destination = destination or self.get_destination()

        if isinstance(items, list):
            if not isinstance(items[0], paginatorinput):
                items = [
                    i
                    if isinstance(i, paginatorinput)
                    else paginatorinput(
                        content=None if isinstance(i, (Embed, File, View)) else i,
                        embed=i if isinstance(i, Embed) else None,
                        file=i if isinstance(i, File) else None,
                        view=i if isinstance(i, View) else None,
                    )
                    for i in items
                ]
            items[0].view = LinkView("https://discord.gg/a2rCNWFUUs", label="Support server")
        else:
            items = (
                items
                if isinstance(items, paginatorinput)
                else paginatorinput(
                    content=None if isinstance(items, (Embed, File, View)) else items,
                    embed=items if isinstance(items, Embed) else None,
                    file=items if isinstance(items, File) else None,
                    view=items if isinstance(items, View) else None,
                )
            )
            items.view = LinkView("https://discord.gg/a2rCNWFUUs", label="Support server")

        await self.context.paginate(items, destination=destination, view=view, **kwargs)

    async def send_bot_help(
        self, mapping: Mapping[Optional[Cog], List[Command]]
    ) -> None:
        await self._send(await self._get_bot_help(mapping))

    async def _get_bot_help(
        self, mapping: Mapping[Optional[Cog], List[Command]]
    ) -> paginatorinput:
        cogs: List[Cog] = sorted(
            [cog for cog in mapping.keys() if cog and await _show(self.context, cog)],
            key=lambda c: c.qualified_name,
        )

        _embed = Embed(colour=self.context.bot.config.colours.neutral).set_image(
            url="attachment://Banner.png"
        )

        _ = "\n".join(f"{cog.qualified_name}: {cog.doc}" for cog in cogs)
        _embed.description = f"```yaml\n{_.strip()}```"
        return paginatorinput(embed=_embed, file=self.context.bot.config.assets.banner)

    async def send_cog_help(self, cog: Cog) -> None:
        if not await _show(self.context, cog):
            await self.send_error_message(
                self.command_not_found(
                    self.context.message.content.removeprefix(
                        f"{self.context.prefix}help "
                    )
                )
            )

        await self._send(await self._get_cog_help(cog))

    async def _get_cog_help(self, cog: Cog) -> Union[List[Embed], Embed]:

        commands: List[Command] = cog.get_commands()

        grouped: List[List[Command]] = [
            i
            for i in [commands[i:PER_PAGE] for i in range(0, len(commands), PER_PAGE)]
            if i
        ]

        embeds = []

        for index, _ in enumerate(grouped):
            desc = "\n".join(f"{c.qualified_name}: {c.short_doc}" for c in _)
            embeds.append(
                Embed(
                    title=cog.qualified_name if index == 0 else "",
                    colour=self.context.bot.config.colours.neutral,
                    description=f"{cog.description if index == 0 else ''}\n\n```yaml\n{desc}```",
                )
            )

        if len(embeds) == 1:
            return embeds[0]
        return embeds

    async def _basic_command_help(self, command: Union[Command, Group]):
        desc = [
            "```",
            self.get_command_signature(command),
            "```",
            command.help or "No help provided!",
        ]

        embed = Embed(
            description="\n".join(desc),
            colour=self.context.bot.config.colours.neutral,
        )

        if command.cog_name:
            embed.add_field(name="Category", value=f"```\n{command.cog_name}```")

        embed.add_field(
            name="Runnable by you, here?",
            value=f"```\n{'Yes' if command in await self.filter_commands([command]) else 'No'}```",
        )

        if getattr(command, "examples", None):
            examples = "\n".join(
                f"{self.context.clean_prefix}{command.qualified_name} {example}"
                for example in command.examples
            )
            embed.add_field(name="Examples", value=f"```\n{examples}```", inline=False)

        return embed

    async def send_command_help(self, command: Command) -> None:
        if not await _show(self.context, command):
            return await self.send_error_message(
                self.command_not_found(
                    self.context.message.content.removeprefix(
                        f"{self.context.prefix}help "
                    )
                )
            )
        await self._send(await self._get_command_help(command))

    async def _get_command_help(self, command: Command) -> Union[List[Embed], Embed]:
        return await self._basic_command_help(command)

    async def send_group_help(self, group: Group):
        if not await _show(self.context, group):
            return await self.send_error_message(
                self.command_not_found(
                    self.context.message.content.removeprefix(
                        f"{self.context.prefix}help "
                    )
                )
            )
        await self._send(await self._get_group_help(group))

    async def _get_group_help(self, group: Group):
        embed = await self._basic_command_help(group)

        embed.description += (
            (
                "\n```yaml\n"
                + "\n".join(f"{c.name}: {c.short_doc}" for c in group.commands)
                + "```"
            )
            if group.commands
            else ""
        )

        return embed

    async def send_error_message(self, error):
        await self._send(
            Embed(
                title="Error!",
                description=f"```\n{error}```",
                colour=self.context.bot.config.colours.bad,
            )
        )


class Help(Cog, hidden=True):
    """
    The help category
    """

    def __init__(self, bot: Nexus):
        self.bot = bot
        self._old_help_command = self.bot.help_command

        _help_command = NexusHelp()
        _help_command.add_check(bot_has_permissions(embed_links=True))

        self.bot.help_command = _help_command
        self.bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._old_help_command


async def setup(bot: Nexus):
    await bot.add_cog(Help(bot))
