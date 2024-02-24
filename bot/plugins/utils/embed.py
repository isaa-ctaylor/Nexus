from datetime import datetime
from typing import Any
from discord.colour import Colour
import discord
from discord.types.embed import EmbedType

GOOD = Colour.from_str("#57F287")
BAD = Colour.from_str("#ED4245")
NEUTRAL = Colour.from_str("#5865F2")


class CustomEmbed(discord.Embed):
    def __init__(
        self,
        message: str | None = None,
        *,
        colour: int | Colour | None = None,
        color: int | Colour | None = None,
        title: Any | None = None,
        type: EmbedType = "rich",
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None
    ):
        if not description and message:
            description = message

        if not timestamp:
            timestamp = datetime.now()

        super().__init__(
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
        )


class SuccessEmbed(CustomEmbed):
    def __init__(
        self,
        message: str | None = None,
        *,
        colour: int | Colour | None = None,
        color: int | Colour | None = None,
        title: Any | None = None,
        type: EmbedType = "rich",
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None
    ):
        if title is None:
            title = "Success!"

        if title is discord.utils.MISSING:
            title = None

        colour = colour or GOOD

        super().__init__(
            message,
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
        )


class ErrorEmbed(CustomEmbed):
    def __init__(
        self,
        message: str | None = None,
        *,
        colour: int | Colour | None = None,
        color: int | Colour | None = None,
        title: Any | None = None,
        type: EmbedType = "rich",
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None
    ):
        if title is None:
            title = "Error!"

        if title is discord.utils.MISSING:
            title = None

        colour = colour or BAD

        super().__init__(
            message,
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
        )


class NeutralEmbed(CustomEmbed):
    def __init__(
        self,
        message: str | None = None,
        *,
        colour: int | Colour | None = None,
        color: int | Colour | None = None,
        title: Any | None = None,
        type: EmbedType = "rich",
        url: Any | None = None,
        description: Any | None = None,
        timestamp: datetime | None = None
    ):
        colour = colour or NEUTRAL

        super().__init__(
            message,
            colour=colour,
            color=color,
            title=title,
            type=type,
            url=url,
            description=description,
            timestamp=timestamp,
        )
