from typing import Any, List, Union
from discord.app_commands.models import Choice
from discord.interactions import Interaction
import wavelink
from discord import app_commands
import discord
import logging
import typing
import difflib
import re
from dateutil.relativedelta import relativedelta
import parsedatetime
import datetime


SIMPLETIME = re.compile(
    """(?:(?P<years>[0-9])(?:years?|y))?
       (?:(?P<months>[0-9]{1,2})(?:months?|mo))?
       (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?
       (?:(?P<days>[0-9]{1,5})(?:days?|d))?
       (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?
       (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?
       (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?
    """,
    re.VERBOSE,
)


class PlayableTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: discord.Interaction, value: str
    ) -> typing.Union[wavelink.Playable, wavelink.Playlist]:
        """Transform a string to a wavelink.Playable

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param value: Value provided by the user
        :type value: str
        :return: The track to play/
        :rtype: wavelink.Playable
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        ret = await wavelink.Playable.search(value)

        if not ret:
            raise app_commands.TransformerError

        return ret

    async def autocomplete(
        self, interaction: discord.Interaction, value: str
    ) -> List[app_commands.Choice[str]]:
        playables = []
        if value:
            playables = await wavelink.Playable.search(value)

        if isinstance(playables, list):
            choices = [
                app_commands.Choice(name=f"{p.title} - {p.author}", value=p.uri)
                for p in playables
            ][:4]
        else:
            choices = [app_commands.Choice(name=playables.name, value=playables.url)]

        if value:
            choices.append(app_commands.Choice(name=value, value=value))

        return choices


class QueueItemTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: Any) -> Any:
        return value

    async def autocomplete(
        self, interaction: discord.Interaction, value: str
    ) -> List[app_commands.Choice[str]]:
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            return []
        if not len(player.queue):
            return []

        options = [
            f"{index + 1}) {item.title}" for index, item in enumerate(player.queue)
        ]

        similar = difflib.get_close_matches(
            value,
            options,
        )

        choices = [app_commands.Choice(name=i, value=i) for i in (similar or options)]
        return choices[:25]


class DatetimeTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: Any) -> Any:
        date_obj = interaction.created_at

        retime = self._check_regex(date_obj, value)

        if retime is not None:
            ret, remaining = retime

        else:
            remaining = self._check_startswith(value)

            times: typing.Tuple[typing.Tuple[datetime.datetime, int, int, int, str]] = (
                parsedatetime.Calendar(version=parsedatetime.VERSION_CONTEXT_STYLE).nlp(
                    remaining, sourceTime=date_obj
                )
            )
            if times is None or len(times) == 0:
                raise app_commands.TransformerError

            dt, timestatus, beginning, end, _ = times[0]

            if not timestatus.hasDateOrTime:
                raise app_commands.TransformerError

            if beginning not in (0, 1) and end != len(value):
                raise app_commands.TransformerError

            if not timestatus.hasTime:
                dt = dt.replace(
                    hour=date_obj.hour,
                    minute=date_obj.minute,
                    second=date_obj.second,
                    microsecond=date_obj.microsecond,
                )

            if timestatus.accuracy == parsedatetime.pdtContext.ACU_HALFDAY:
                dt = dt.replace(day=date_obj.day + 1)

            ret = dt.replace(tzinfo=datetime.timezone.utc)

        return ret

    def _check_regex(self, dt, argument):
        remaining = argument
        match = SIMPLETIME.match(remaining)
        if match is None or not match.group(0):
            return None
        while match is not None and match.group(0):
            data = {k: int(v) for k, v in match.groupdict(default=0).items()}
            remaining = str(remaining[match.end() :]).strip()
            dt += relativedelta(**data)

            match = SIMPLETIME.match(remaining)

        ret = dt
        return ret, remaining

    def _check_startswith(self, reason: str):
        if reason.startswith("me") and reason[:6] in (
            "me to ",
            "me in ",
            "me at ",
        ):
            reason = reason[6:]

        if reason[:2] == "me" and reason[:9] == "me after ":
            reason = reason[9:]

        if reason[:3] == "me ":
            reason = reason[3:]

        if reason[:2] == "me":
            reason = reason[2:]

        if reason[:6] == "after ":
            reason = reason[6:]

        if reason[:5] == "after":
            reason = reason[5:]

        if reason.endswith("from now"):
            reason = reason[:-8]

        return reason.strip()
