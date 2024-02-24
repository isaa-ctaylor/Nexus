import re
import asyncio
import contextlib
import logging
import typing

import discord
import wavelink
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot
from wavelink import Player

from .utils import hyperlink
from .utils.embed import ErrorEmbed, NeutralEmbed, SuccessEmbed
from .utils.transformer import PlayableTransformer, QueueItemTransformer
from .utils.view import Confirm
from datetime import datetime

TIMEOUT = 300  # 5 minutes


class MusicException(Exception):
    """Base exception for music plugin errors!"""


class BotNotInVoiceChannel(MusicException):
    """I am not in a voice channel!"""


class UserNotInSameVoiceChannel(MusicException):
    """User not in the same voice channel as the bot"""

    def __init__(self, channel: discord.VoiceChannel) -> None:
        self.channel = channel


class UserNotInVoiceChannel(MusicException):
    """You are not in a voice channel!"""


class NoPermissionToJoin(MusicException):
    """No permission to join channel"""

    def __init__(self, channel: discord.VoiceChannel) -> None:
        self.channel = channel


class AlreadyPaused(MusicException):
    """The player is already paused!"""


class NotPaused(MusicException):
    """The player is not paused!"""


class NothingPlaying(MusicException):
    """Nothing is playing right now!"""


class QueueItemMissing(MusicException):
    """Please select a queue item from the autocomplete list"""


class Music(Cog):
    """Music commands"""

    def __init__(self, bot: Bot):
        self.bot = bot

        self._tasks: typing.Dict[int, asyncio.Task] = {}

        self.logger = logging.getLogger("discord.bot.plugins.Music")

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original

        if isinstance(
            error,
            (
                BotNotInVoiceChannel,
                UserNotInVoiceChannel,
                AlreadyPaused,
                NotPaused,
                NothingPlaying,
                QueueItemMissing,
            ),
        ):
            message = error.__doc__

        elif isinstance(error, UserNotInSameVoiceChannel):
            message = f"I am already in {error.channel.mention}!"
        elif isinstance(error, NoPermissionToJoin):
            message = f"I don't have permission to join {error.channel.mention}!"
        elif isinstance(error, app_commands.TransformerError):
            message = f"Couldn't find a song matching '{error.value}'"

        else:
            message = f"An error occured. If the issue persists, please contact the support team."
            self.logger.error(
                str(error), exc_info=(type(error), error, error.__traceback__)
            )

        embed = ErrorEmbed(message)

        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=embed)

    @commands.Cog.listener(name="on_voice_state_update")
    async def _on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.id != self.bot.user.id:
            return

        if after.channel and not before.channel:
            await self._on_wavelink_track_end(
                wavelink.TrackEndEventPayload(
                    after.channel.guild.voice_client, None, "joined"
                )
            )

    @commands.Cog.listener(name="on_wavelink_player_update")
    async def _on_wavelink_player_update(
        self, payload: wavelink.PlayerUpdateEventPayload
    ) -> None:
        if payload.player:
            self.logger.debug(
                f"Player update in guild {payload.player.guild.name} ({payload.player.guild.id}) connected={payload.connected} latency={payload.ping}"
            )

    @commands.Cog.listener(name="on_wavelink_track_start")
    async def _on_wavelink_track_start(
        self, payload: wavelink.TrackStartEventPayload
    ) -> None:
        await self._send_current_playing(payload.player.channel, payload.player)

    @commands.Cog.listener(name="on_wavelink_track_end")
    async def _on_wavelink_track_end(
        self, payload: wavelink.TrackEndEventPayload
    ) -> None:
        player: Player = payload.player

        if not player:
            return

        self.logger.debug(
            f"{payload.reason} in guild {player.guild.name} ({player.guild.id})"
        )
        try:
            playable = player.queue.get()
            await player.play(playable)
        except wavelink.QueueEmpty:
            try:
                task = self.bot.loop.create_task(
                    asyncio.wait_for(player.queue.get_wait(), TIMEOUT)
                )
                self._tasks[player.channel.id] = task
                try:
                    playable = await task
                    await player.play(playable)
                except asyncio.CancelledError:
                    self.logger.debug(
                        f"{payload.player.guild.name} ({payload.player.guild.id}) Retrieving next song cancelled"
                    )
                finally:
                    self._tasks.pop(player.channel.id, None)
            except asyncio.TimeoutError:
                await player.disconnect()
                now = datetime.utcnow()
                await player.channel.send(
                    embed=SuccessEmbed(
                        "👋 Disconnected due to inactivity",
                        title=discord.utils.MISSING,
                        timestamp=now,
                    )
                )
                self.logger.debug(
                    f"{payload.player.guild.name} ({payload.player.guild.id}) Timed out getting next song."
                )

    async def _send_current_playing(
        self,
        responseorchannel: typing.Union[
            discord.TextChannel, discord.InteractionResponse
        ],
        player: Player,
    ) -> None:
        current = player.current

        embed = NeutralEmbed(title=current.title, url=current.uri)
        embed.set_thumbnail(url=current.artwork)
        embed.add_field(name="Artist", value=current.author)
        embed.add_field(name="Source", value=current.source.capitalize())

        if extras := self.bot.voice_extras.get(player.guild.id, None):
            if msg := extras.get("last_current_message", None):
                with contextlib.suppress(
                    discord.NotFound, discord.Forbidden, discord.HTTPException
                ):
                    await msg.delete()

        if isinstance(responseorchannel, discord.InteractionResponse):
            msg = await responseorchannel.send_message(embed=embed)
        else:
            msg = await responseorchannel.send(embed=embed)

        if not self.bot.voice_extras.get(player.guild.id):
            self.bot.voice_extras[player.guild.id] = {}
        self.bot.voice_extras[player.guild.id]["last_current_message"] = msg

    @app_commands.command(name="join")
    async def _join(
        self,
        interaction: discord.Interaction,
        channel: typing.Optional[discord.VoiceChannel],
    ) -> None:
        """Join a voice channel

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param channel: Channel to join
        :type channel: typing.Optional[discord.VoiceChannel]
        """
        if not channel:
            if not interaction.user.voice:
                raise UserNotInVoiceChannel
            else:
                channel = interaction.user.voice.channel

        if (
            interaction.guild.me.voice
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            if interaction.user.guild_permissions.move_members:
                c = Confirm()

                await interaction.response.send_message(
                    embed=NeutralEmbed(
                        f"I am already in {interaction.guild.me.voice.channel.mention}.\nPress confirm to move me to {channel.mention}.",
                        title="Confirm move",
                    ),
                    view=c,
                    ephemeral=True,
                )
                c.message = await interaction.original_response()

                if await c.wait():
                    return

                if not c.value:
                    return

                interaction = c.interaction
            else:
                raise UserNotInSameVoiceChannel(
                    interaction.guild.me.voice.channel.mention
                )

        if not channel.permissions_for(channel.guild.me).connect:
            raise NoPermissionToJoin(channel)
        else:
            await interaction.response.defer(thinking=True)
            try:
                await channel.connect(self_deaf=True, cls=Player)
                await interaction.followup.send(
                    embed=SuccessEmbed(f"Joined channel {channel.mention}")
                )
            # We have already checked if the user has relevant permissions,
            # so it is safe to default to moving channel
            except discord.ClientException:
                player: Player = interaction.guild.voice_client
                await player.move_to(channel, self_deaf=True)
                await interaction.edit_original_response(
                    embed=SuccessEmbed(f"Joined channel {channel.mention}")
                )

    @app_commands.command(name="disconnect")
    async def _disconnect(self, interaction: discord.Interaction) -> None:
        """Disconnect from a voice channel

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        if not interaction.guild.me.voice:
            raise BotNotInVoiceChannel()

        if (
            not interaction.user.voice
            and not interaction.user.guild_permissions.move_members
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInVoiceChannel()

        if (
            interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            c = Confirm()

            await interaction.response.send_message(
                embed=NeutralEmbed(
                    "You are not in the same channel as me, please confirm."
                ),
                view=c,
                ephemeral=True,
            )

            if await c.wait():
                return

            if not c.value:
                return

            interaction = c.interaction

        channel: discord.VoiceChannel = interaction.guild.voice_client.channel
        await interaction.guild.voice_client.disconnect()
        task = self._tasks.get(channel.id, None)
        if task:
            self.logger.debug(
                f"Cleaning up waiters in {channel.guild.name} ({channel.guild.id})"
            )
            task.cancel()
        await interaction.response.send_message(
            embed=SuccessEmbed(f"Disconnected from {channel.mention}")
        )

    @app_commands.command(name="play")
    @app_commands.rename(playable="query")
    async def _play(
        self,
        interaction: discord.Interaction,
        playable: app_commands.Transform[wavelink.Playable, PlayableTransformer],
    ) -> None:
        """Play a song, playlist or album

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param playable: Search query
        :type playable: app_commands.Transform[wavelink.Playable, PlayableTransformer]
        :raises UserNotInVoiceChannel: User not in voice channel
        """
        if not interaction.user.voice:
            raise UserNotInVoiceChannel

        if not interaction.guild.voice_client:
            player: wavelink.Player = await interaction.user.voice.channel.connect(
                self_deaf=True, cls=wavelink.Player
            )

        player: Player = interaction.guild.voice_client
        if isinstance(playable, list):
            playable = playable[0]
        player.queue.put(playable)

        if isinstance(playable, wavelink.Playlist):
            title = playable.name
            url = playable.url
        else:
            title = playable.title
            url = playable.uri

        await interaction.followup.send(
            embed=SuccessEmbed(f"Added {hyperlink(title, url)} to the queue"),
            ephemeral=True,
        )

    @app_commands.command(name="pause")
    async def _pause(self, interaction: discord.Interaction) -> None:
        """Pause the player

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        if not interaction.guild.voice_client:
            raise BotNotInVoiceChannel

        if (
            not interaction.user.voice
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInVoiceChannel

        if (
            interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInSameVoiceChannel

        player: Player = interaction.guild.voice_client

        if player.paused:
            raise AlreadyPaused

        await player.pause(True)
        await interaction.response.send_message(
            embed=SuccessEmbed("Paused the player."), ephemeral=True
        )

    @app_commands.guild_only
    @app_commands.command(name="resume")
    async def _resume(self, interaction: discord.Interaction) -> None:
        """Resume the player

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        if not interaction.guild.voice_client:
            raise BotNotInVoiceChannel

        if (
            not interaction.user.voice
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInVoiceChannel

        if (
            interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInSameVoiceChannel

        player: Player = interaction.guild.voice_client

        if not player.paused:
            raise NotPaused

        await player.pause(False)
        await interaction.response.send_message(
            embed=SuccessEmbed("Resumed the player."), ephemeral=True
        )

    queue = app_commands.Group(name="queue", description="Queue")

    @queue.command(name="list")
    async def _queue_list(self, interaction: discord.Interaction) -> None:
        """Show the queue

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        if not interaction.guild.voice_client:
            raise BotNotInVoiceChannel

        if (
            not interaction.user.voice
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInVoiceChannel

        if (
            interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInSameVoiceChannel

        player: Player = interaction.guild.voice_client

        current = player.current
        queue = player.queue

        if len(queue) == 0:
            return await self._nowplaying.callback(self, interaction)

        embed = NeutralEmbed(
            title=f"{len(queue)} item{'s' if len(queue) != 1 else ''} in queue"
        )
        lines = []

        lines.append(f"**Currently playing:** {hyperlink(current.title, current.uri)}")

        for index, item in enumerate(list(queue)):
            lines.append(f"{index+1}) {hyperlink(item.title, item.uri)}")
            if len("\n".join(lines)) > 4096:
                lines.pop()
                break

        embed.description = "\n".join(lines)

        await interaction.response.send_message(embed=embed)

    @queue.command(name="remove")
    async def _queue_remove(
        self,
        interaction: discord.Interaction,
        item: app_commands.Transform[str, QueueItemTransformer],
    ) -> None:
        """Remove an item from the queue

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param item: Item to remove
        :type item: str
        """
        player: Player = interaction.guild.voice_client
        if not player:
            raise BotNotInVoiceChannel

        if (
            not interaction.user.voice
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInVoiceChannel

        if (
            interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInSameVoiceChannel

        match = re.match(r"^(\d+)(\)|)", item)
        if not match:
            raise QueueItemMissing

        item = int(match.group(1)) - 1

        removed = player.queue._queue[item]
        await player.queue.delete(item)

        await interaction.response.send_message(
            embed=SuccessEmbed(f"Removed {removed} from the queue"), ephemeral=True
        )

    @app_commands.command(name="nowplaying")
    async def _nowplaying(self, interaction: discord.Interaction) -> None:
        """Show the currently playing song

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        if not interaction.guild.voice_client:
            raise BotNotInVoiceChannel

        if (
            not interaction.user.voice
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInVoiceChannel

        if (
            interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id
            and len(interaction.guild.me.voice.channel.members) > 1
        ):
            raise UserNotInSameVoiceChannel

        player: Player = interaction.guild.voice_client

        current = player.current

        if not current:
            raise NothingPlaying

        await self._send_current_playing(interaction.response, player)

    @app_commands.command(name="skip")
    async def _skip(self, interaction: discord.Interaction) -> None:
        """Skip the current song

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        if not interaction.guild.voice_client:
            raise BotNotInVoiceChannel

        if not interaction.user.voice:
            raise UserNotInVoiceChannel

        if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
            raise UserNotInSameVoiceChannel

        player: Player = interaction.guild.voice_client

        skipped: typing.Optional[wavelink.Playable] = await player.skip()

        if not skipped:
            raise NothingPlaying

        else:
            await interaction.response.send_message(
                embed=SuccessEmbed(f"Skipped {hyperlink(skipped.title, skipped.uri)}")
            )

    @app_commands.command(name="loop")
    @app_commands.rename(type_="type")
    async def _loop(
        self,
        interaction: discord.Interaction,
        type_: typing.Optional[typing.Literal["off", "one", "all"]] = None,
    ) -> None:
        """Loop the queue

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param type_: Loop type
        :type type_: typing.Optional[typing.Literal["off", "one", "all"]], optional
        """
        player: Player = interaction.guild.voice_client

        if not player:
            raise BotNotInVoiceChannel

        if not interaction.user.voice:
            raise UserNotInVoiceChannel

        if interaction.user.voice.channel.id != interaction.guild.me.voice.channel.id:
            raise UserNotInSameVoiceChannel

        if not player.current:
            raise NothingPlaying

        m = {
            wavelink.QueueMode.normal: wavelink.QueueMode.loop_all,
            wavelink.QueueMode.loop_all: wavelink.QueueMode.loop,
            wavelink.QueueMode.loop: wavelink.QueueMode.normal,
        }

        sm = {
            "off": wavelink.QueueMode.normal,
            "one": wavelink.QueueMode.loop,
            "all": wavelink.QueueMode.loop_all,
        }

        if not type_:
            player.queue.mode = m[player.queue.mode]
        else:
            player.queue.mode = sm[type_]

        await interaction.response.send_message(
            embed=SuccessEmbed(
                f"Changed the loop mode to {str(player.queue.mode).removeprefix('QueueMode.').replace('_', ' ').capitalize()}"
            )
        )


async def setup(bot: Bot):
    await bot.add_cog(Music(bot))
