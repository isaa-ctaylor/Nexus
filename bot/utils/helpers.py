import asyncio
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, List, Union

from discord import Embed, File, Forbidden, HTTPException, Message, NotFound
from discord.abc import Messageable
from discord.colour import Colour
from discord.ext.commands import Bot, Context
from discord.mentions import AllowedMentions


class DotDict(dict):
    """
    A `dict` subclass that implements dot notation
    """

    def _format_array(
        self,
        array: list,
        *,
        tuple_: bool = False
    ) -> Union[list, tuple]:
        data = [
            DotDict(element)
            if isinstance(element, dict)
            else self._format_list(element)
            if isinstance(element, list)
            else element
            for element in array
        ]

        return tuple(data) if tuple_ else list(data)

    def __getattr__(self, key: str) -> Any:
        try:
            value = self[key]
        except KeyError as e:
            raise AttributeError(e)

        if isinstance(value, dict):
            return DotDict(value)

        if isinstance(value, (list, tuple)):
            return self._format_array(
                value,
                tuple_=not isinstance(value, list)
            )

        if isinstance(value, str) and value.startswith("!Colour "):
            return Colour(int(value.split()[1]))

        return value

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError as e:
            raise AttributeError(e)

    def __repr__(self) -> str:
        return f"<DotDict {dict.__repr__(self)}>"


@dataclass
class paginatorinput:
    content: Union[str, None] = None
    embed: Union[Embed, None] = None
    file: Union[File, None] = None


REACTIONS = {
    "⏮": "first",
    "◀": "previous",
    "🗑": "delete",
    "▶": "next",
    "⏭": "last"
}


class Paginator:
    """
    A paginator
    """

    def __init__(self, ctx: Union[Context, Any], **kwargs):
        self.items: List[paginatorinput] = None

        self.message: Message = None
        self.reply: bool = bool(kwargs.pop("reply", True))
        self.sent: bool = False

        self.ctx = ctx
        self.bot: Union[Bot, Any] = ctx.bot

        self.user = None

        self.remove_reactions: bool = bool(
            kwargs.pop("remove_reactions", True)
        )
        self.two_way_reactions: bool = bool(
            kwargs.pop("two_way_reactions", True)
        )

        self.stopemoji = kwargs.pop("stopemoji", "\U0001f5d1")

        self.emojis: list = []
        self.commands: list = []

        self.auto_footer: bool = bool(kwargs.pop("auto_footer", False))
        self.timeout: float = float(kwargs.pop("timeout", 60))

        self.current_page: int = 0

        reactions = kwargs.pop("reactions", REACTIONS)

        if reactions:
            for reaction, action in reactions.items():
                self.add_reaction(str(reaction), str(action))

    def add_reaction(self, emoji: str, command: str):
        if not self.sent:
            self.emojis.append(str(emoji))
            self.commands.append(command)

    def remove_reaction(self, emoji):
        if not self.sent:
            with suppress(ValueError):
                index = self.emojis.index(emoji)
                self.emojis.pop(index)
                self.commands.pop(index)

    def insert_reaction(self, index, emoji, command):
        if not self.sent:
            self.emojis.insert(index, emoji)
            self.commands.insert(index, command)

    async def _clear_reactions(self):
        try:
            await self.message.clear_reactions()
        except HTTPException:
            for emoji in self.emojis:
                try:
                    await self.message.clear_reaction(emoji)
                except HTTPException:
                    with suppress(HTTPException, Forbidden):
                        await self.message.remove_reaction(
                            emoji, self.ctx.guild.me
                        )

    async def _remove_reaction(self, emoji, member):
        with suppress(HTTPException, Forbidden):
            await self.message.remove_reaction(emoji, member)

    def _reaction_check(self, reaction, user):
        return (
            str(reaction.emoji) in [*self.emojis, self.stopemoji]
            and (
                (user.id == self.ctx.author.id)
                if not self.user
                else (user.id == self.user.id)
            )
            and reaction.message.id == self.message.id
        )

    async def waitmany(self):
        done, pending = await asyncio.wait(
            [
                self.bot.wait_for("reaction_add", check=self._reaction_check),
                self.bot.wait_for(
                    "reaction_remove", check=self._reaction_check
                ),
            ],
            return_when=asyncio.FIRST_COMPLETED,
            timeout=self.timeout,
        )
        if not done:
            raise asyncio.TimeoutError
        try:
            reaction, user = done.pop().result()
        except asyncio.TimeoutError:
            await self._clear_reactions()
        for future in done:
            future.exception()
        for future in pending:
            future.cancel()

        return reaction, user

    async def wait(self):
        reaction, user = await self.bot.wait_for(
            "reaction_add", check=self._reaction_check, timeout=self.timeout
        )
        return reaction, user

    async def edit(self):
        if self.sent:
            await self.message.edit(
                content=self.items[self.current_page].content,
                embed=self.items[self.current_page].embed,
                allowed_mentions=AllowedMentions.none(),
            )

    async def next(self):
        self.current_page = min(self.current_page + 1, len(self.items) - 1)

    async def previous(self):
        self.current_page = max(self.current_page - 1, 0)

    async def first(self):
        self.current_page = 0

    async def last(self):
        self.current_page = len(self.items) - 1

    async def stop(self):
        await self._clear_reactions()
        return False

    async def delete(self):
        with suppress(NotFound):
            await self.message.delete()
        with suppress(NotFound):
            await self.ctx.message.add_reaction("\U00002705")
        return False

    async def handle_command(self, command):
        commanddict = {
            "next": self.next,
            "previous": self.previous,
            "first": self.first,
            "last": self.last,
            "stop": self.stop,
            "delete": self.delete,
        }

        _func = commanddict[command]

        carry_on = await _func()

        if _func in {self.delete, self.stop}:
            return carry_on if carry_on is not None else True

        await self.edit()

        if self.remove_reactions:
            await self._remove_reaction(
                self.emojis[self.commands.index(command)], self.ctx.author
            )

        if carry_on is None:
            return True
        return carry_on

    def get_command(self, emoji):
        return self.commands[self.emojis.index(emoji)]

    async def send(
        self,
        items: List[paginatorinput],
        *,
        destination: Messageable = None,
        start: int = 0,
    ):
        destination = destination or self.ctx.channel

        self.items = [
            paginatorinput(embed=item)
            if isinstance(item, Embed)
            else paginatorinput(file=item)
            if isinstance(item, File)
            else paginatorinput(str(item))
            for item in items
        ]

        self.message = await destination.send(
            self.items[start].content,
            embed=self.items[start].embed,
            file=self.items[start].file,
            reference=self.ctx.message if self.reply else None,
            mention_author=False,
        )

        self.sent = True

        if len(self.items) == 1:
            await self.message.add_reaction(self.stopemoji)
            with suppress(asyncio.TimeoutError):
                await self.wait()
                await self.delete()
                return
            await self.stop()
            return

        for emoji in self.emojis:
            await self.message.add_reaction(str(emoji))

        carry_on = True

        while carry_on:
            try:
                if self.two_way_reactions:
                    reaction, _ = await self.waitmany()
                else:
                    reaction, _ = await self.wait()

                carry_on = await self.handle_command(
                    self.get_command(str(reaction.emoji))
                )
                if carry_on:
                    await asyncio.sleep(0.5)  # Prevent abuse
            except asyncio.TimeoutError:
                carry_on = await self.stop()
