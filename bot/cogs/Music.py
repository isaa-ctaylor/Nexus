import asyncio
import datetime
import math
import random
import re
from contextlib import suppress
from os import getenv
from typing import Any, Dict, Optional, Union

import async_timeout
import discord
import wavelink
from discord import (
    ClientException,
    Embed,
    Member,
    TextChannel,
    VoiceChannel,
    VoiceProtocol,
)
from discord.ext.commands import CommandError, Converter, guild_only
from discord.opus import OpusNotLoaded
from utils import codeblocksafe, hyperlink
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import command
from utils.subclasses.context import NexusContext
from wavelink.ext import spotify
from wavelink.utils import MISSING

SPOTIFY = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)
SPOTIFY_REQUEST = "https://api.spotify.com/v1/{type}s/{id}"


class Player(wavelink.Player):
    control_channel: TextChannel
    skippers: set = set()
    
    shuffled: bool = False
    original_queue: wavelink.WaitQueue

    def __call__(
        self,
        client: discord.Client = MISSING,
        channel: VoiceChannel = MISSING,
        *,
        node: wavelink.Node = MISSING,
    ):
        self.client: discord.Client = client
        self.channel: VoiceChannel = channel

        if node is MISSING:
            node = wavelink.NodePool.get_node()
        self.node: wavelink.Node = node
        self.node._players.append(self)

        self._voice_state: Dict[str, Any] = {}

        self.last_update: datetime.datetime = MISSING
        self.last_position: float = MISSING

        self.volume: float = 100
        self._paused: bool = False
        self._source: Optional[wavelink.abc.Playable] = None
        # self._equalizer = Equalizer.flat()

        self.queue = wavelink.WaitQueue()


class SpotifyException(Exception):
    ...


class Query(Converter):
    async def convert(self, ctx: NexusContext, argument: str):
        async with ctx.typing():
            if decoded := spotify.decode_url(argument):
                if decoded["type"] in [
                    spotify.SpotifySearchType.track,
                    spotify.SpotifySearchType.playlist,
                    spotify.SpotifySearchType.album,
                ]:
                    _ = await spotify.SpotifyTrack.search(
                        decoded["id"],
                        type=decoded["type"],
                        return_first=decoded["type"] == spotify.SpotifySearchType.track,
                    )

                    return _
            with suppress(Exception):
                _ = await wavelink.YouTubePlaylist.convert(ctx, argument)
                if _:
                    return _
            with suppress(Exception):
                _ = await wavelink.YouTubeTrack.convert(ctx, argument)
                if _:
                    return _
            with suppress(Exception):
                _ = await wavelink.YouTubeMusicTrack.convert(ctx, argument)
                if _:
                    return _

        raise CommandError("Could not find any songs matching that query.")


class Music(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    async def cog_load(self):
        if not getattr(self.bot, "wavelink", None):
            self.bot.wavelink = await wavelink.NodePool.create_node(
                bot=self.bot,
                host="127.0.0.1",
                port=2333,
                password="youshallnotpass",
                spotify_client=spotify.SpotifyClient(
                    client_id=getenv("SPOTIFY_ID"),
                    client_secret=getenv("SPOTIFY_SECRET"),
                ),
            )

    def required(self, ctx: NexusContext):
        player: Player = ctx.voice_client
        channel = self.bot.get_channel(int(player.channel.id))
        return math.ceil((len(channel.members) - 1) / 2.5)

    @Cog.listener(name="on_wavelink_track_end")
    async def _play_next_or_disconnect(
        self, player: Player, track: wavelink.Track, reason=None
    ):
        if reason not in ("FINISHED", "STOPPED", "ERRORED"):
            return
        try:
            with async_timeout.timeout(300):  # 5 minutes
                track = await player.queue.get_wait()
                await player.play(track)
                await player.control_channel.send(
                    embed=Embed(
                        description=f"Now playing: `{codeblocksafe(track.title)}` | {track.requester.mention}",
                        colour=self.bot.config.colours.neutral,
                    )
                )
        except asyncio.TimeoutError:
            if player.is_playing():
                return
            await player.disconnect()
            await player.control_channel.send(
                embed=Embed(
                    description="👋 Disconnected due to inactivity.",
                    colour=self.bot.config.colours.neutral,
                )
            )

    @Cog.listener(name="on_wavelink_track_exception")
    async def _track_exception(self, player: Player, track: wavelink.Track, error: Any):
        await self._play_next_or_disconnect(player, track, "ERRORED")

    @command(name="connect", aliases=["join"], usage="[channel]")
    async def _connect(
        self,
        ctx: NexusContext,
        channel: Optional[VoiceChannel] = None,
        /,
        invoked=False,
    ):
        """
        Connect Nexus to a voice channel
        """
        if not channel:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                return await ctx.error(
                    "Please join and/or specify a channel for me to join!"
                )

        if vc := ctx.voice_client:
            if vc.channel.id == channel.id:
                return await ctx.error(f"Already connected to {channel.name}!")
            if not ctx.author.guild_permissions.manage_guild:
                return await ctx.error(
                    f"I am already connected to a channel! ({channel.name})"
                )

        try:
            _ = await channel.connect(self_deaf=True, cls=Player)
            _.control_channel = ctx.channel
            if not invoked:
                await ctx.embed(
                    description=f"Connected to {channel.mention}", paginate=False
                )
            if not _.is_playing():
                self.bot.loop.create_task(
                    self._play_next_or_disconnect(
                        self.bot.wavelink.get_player(ctx.guild), None, "STOPPED"
                    )
                )
            return
        except TimeoutError:
            return await ctx.error("Connecting timed out...")
        except ClientException:
            return await ctx.error("I am already connected to a channel!")
        except OpusNotLoaded:
            return await ctx.error("Sorry! I couldn't do that. Try again soon.")

    @guild_only()
    @command(name="play")
    async def _play(self, ctx: NexusContext, *, query: Query = None):
        """
        Play a song. This can be from spotify or youtube.

        Can also be used as shorthand for the `resume` command
        """
        if not query:
            return await self._resume(ctx)

        async with ctx.typing():
            if not ctx.voice_client:
                await self._connect(ctx, invoked=True)

            if isinstance(query, wavelink.YouTubePlaylist):
                tracks = query.tracks
            elif isinstance(query, list):
                tracks = query
            else:
                tracks = [query]

            for track in tracks:
                track.requester = ctx.author
                track.ctx = ctx

            player: Player = self.bot.wavelink.get_player(ctx.guild)
            player.queue.extend(tracks)

            _ = (
                f"`{codeblocksafe(tracks[0].title)}`"
                if len(tracks) == 1
                else f"{len(tracks)} tracks"
            )
        return await ctx.embed(description=f"Added {_} to the queue", paginate=False)

    @guild_only()
    @command(name="disconnect", aliases=["leave", "dc"])
    async def _disconnect(self, ctx: NexusContext):
        """
        Disconnect from the current voice channel
        """
        if not ctx.voice_client:
            return await ctx.error("I am not in a voice channel!")
        if not ctx.author.voice:
            if len(ctx.me.voice.channel.members) != 1:
                return await ctx.error("You are not in a voice channel!")
        else:
            if ctx.author.voice.channel != ctx.me.voice.channel:
                return await ctx.error("You are not in the same voice channel as me!")

        with suppress(Exception):
            await self.bot.wavelink.get_player(ctx.guild).disconnect()
            await ctx.message.add_reaction("👍")

    @guild_only()
    @command(name="skip")
    async def _skip(self, ctx: NexusContext):
        """
        Skip the current song
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice and ctx.author.voice.channel.id != player.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if (
            ctx.author.id != player.track.requester.id
            or not ctx.author.guild_permissions.manage_guild
        ):
            required = self.required(ctx)

            _ = player.skippers.copy()
            player.skippers.add(ctx.author.id)

            if player.skippers == _:
                return await ctx.send(
                    "You have already voted to skip!", mention_author=False
                )

            if len(player.skippers) < required:
                return await ctx.reply(
                    f"Voted to skip ({len(player.skippers)}/{required})"
                )

        player.skippers.clear()

        await player.stop()
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(name="queue")
    async def _queue(self, ctx: NexusContext):
        """
        See the current queue
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        pages = [
            list(player.queue)[i : i + 10] for i in range(0, len(player.queue), 10)
        ]

        embeds = [
            Embed(
                description="\n".join(
                    f"{list(player.queue).index(t) + 1}) {hyperlink(f'`{t.title}`', t.uri)}"
                    for t in l
                ),
                colour=self.bot.config.colours.neutral,
            )
            for l in pages
        ]

        if not embeds:
            embeds = [Embed(colour=self.bot.config.colours.neutral)]

        embeds[0].description = (
            f"**Now playing**: {hyperlink(player.track.title, player.track.uri)}\n\n"
            + (
                embeds[0].description.strip()
                if isinstance(embeds[0].description, str)
                else ""
            )
        )

        if thumb := getattr(player.track, "thumbnail", None):
            embeds[0].set_thumbnail(url=thumb)

        await ctx.paginate(embeds)

    @guild_only()
    @command(name="remove")
    async def _remove(self, ctx: NexusContext, index: int):
        """
        Remove a song from the queue
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice and ctx.author.voice.channel.id != player.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        try:
            track: wavelink.Track = list(player.queue._queue)[index - 1]
        except IndexError:
            return await ctx.error("Please provide a valid song index!")

        if track.requester.id != ctx.author.id and track.requester.id in [
            m.id for m in player.channel.members
        ]:
            return await ctx.error("You did not request this song!")

        del player.queue[index - 1]
        await ctx.embed(
            description=f"👍 Removed `{codeblocksafe(track.title)}` from the queue"
        )

    @guild_only()
    @command(name="pause")
    async def _pause(self, ctx: NexusContext):
        """
        Pause the current song
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice and ctx.author.voice.channel.id != player.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if player.is_paused():
            return await ctx.error("The player is already paused!")

        await player.set_pause(True)
        await ctx.message.add_reaction("👍")

        try:
            await self.bot.wait_for(
                "command",
                check=lambda ctx: ctx.command.name in ["resume", "play"],
                timeout=300,
            )
        except asyncio.TimeoutError:
            if not player.is_playing():
                await player.disconnect()
                await player.control_channel.send(
                    embed=Embed(
                        description="👋 Disconnected due to inactivity.",
                        colour=self.bot.config.colours.neutral,
                    )
                )

    @guild_only()
    @command(name="resume")
    async def _resume(self, ctx: NexusContext):
        """
        Resume the paused song
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice and ctx.author.voice.channel.id != player.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if not player.is_paused():
            return await ctx.error("The player is not paused!")

        await player.set_pause(False)
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(name="volume")
    async def _volume(self, ctx: NexusContext, volume: Union[int, str]):
        """
        Set the volume of the player

        Please allow 10 seconds for the volume to update
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice and ctx.author.voice.channel.id != player.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if isinstance(volume, str):
            if volume.lower() == "reset":
                volume = 100
            else:
                return await ctx.error(
                    'Please specify a number between 1 and 200, or "reset"'
                )

        if volume > 200 or volume < 1:
            return await ctx.error(
                'Please specify a number between 1 and 200, or "reset"'
            )

        await player.set_volume(volume)
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(name="now")
    async def _now(self, ctx: NexusContext):
        """
        See what song is currently playing
        """
        player: Player = ctx.voice_client
        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        await ctx.paginate(
            Embed(
                title="Currently playing",
                description=f"{hyperlink(f'`{player.track.title}`', player.track.uri)} requested by {player.track.ctx.author.mention}",
                colour=self.bot.config.colours.neutral,
            )
            .set_image(url=getattr(player.track, "thumbnail", None))
            .add_field(
                name="Position",
                value=f"{int(math.floor(player.track.length/player.position)/10)*'🟪'}{(10-int(math.floor(player.track.length/player.position)/10))*'⬛'} [{datetime.timedelta(seconds=int(player.position))}/{datetime.timedelta(seconds=int(player.track.length))}]",
            )
        )
        
    @guild_only()
    @command(name="shuffle")
    async def _shuffle(self, ctx: NexusContext):
        """
        Toggle the shuffle of the queue
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice and ctx.author.voice.channel.id != player.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")
        
        if player.shuffled:
            player.queue = player.original_queue.copy()
            player.shuffled = False
            return await ctx.embed(description=f"Shuffle toggled off")
        else:
            player.original_queue = player.queue.copy()
            random.shuffle(player.queue._queue)
            player.shuffled = True
            return await ctx.embed(description=f"Shuffle toggled on")


async def setup(bot: Nexus):
    await bot.add_cog(Music(bot))
