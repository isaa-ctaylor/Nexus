import asyncio
import datetime
import re
from contextlib import suppress
from os import getenv
from typing import Any, Dict, Optional, Union

import async_timeout
import discord
import wavelink
from discord import ClientException, Member, TextChannel, VoiceChannel, VoiceProtocol
from discord.ext.commands import CommandError, Converter
from discord.opus import OpusNotLoaded
from utils import codeblocksafe
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
    requester: Member
    
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
        if decoded := spotify.decode_url(argument):
            if decoded["type"] in [
                spotify.SpotifySearchType.track,
                spotify.SpotifySearchType.playlist,
                spotify.SpotifySearchType.album,
            ]:
                _ = await spotify.SpotifyTrack.search(
                    decoded["id"], type=decoded["type"]
                )

                return _
        with suppress(Exception):
            _ = await wavelink.YouTubePlaylist.convert(ctx, argument)
            if _: return _
        with suppress(Exception):
            _ = await wavelink.YouTubeTrack.convert(ctx, argument)
            if _: return _
        with suppress(Exception):
            _ = await wavelink.YouTubeMusicTrack.convert(ctx, argument)
            if _: return _
        
        raise CommandError("Could not find any songs matching that query.")

class NewMusic(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    async def cog_load(self):
        await self.bot.wait_until_ready()

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

    @Cog.listener(name="on_wavelink_track_end")
    async def _play_next_or_disconnect(self, player: Player, track: wavelink.Track, reason = None):
        if reason not in ("FINISHED", "STOPPED", "ERRORED"):
            return
        try:
            with async_timeout.timeout(300): # 5 minutes
                track = await player.queue.get_wait()
                await player.play(track)
                await player.control_channel.send(f"Now playing: `{codeblocksafe(track.title)}`")
        except asyncio.TimeoutError:
            if player.is_playing():
                return
            await player.control_channel.send("👋 Disconnected due to inactivity.")
            await player.disconnect()

    @Cog.listener(name="on_wavelink_track_exception")
    async def _track_exception(self, player: Player, track: wavelink.Track, error: Any):
        await self._play_next_or_disconnect(player, track, "ERRORED")

    @command(name="connect", aliases=["join"], usage="[channel]")
    async def _connect(self, ctx: NexusContext, channel: Optional[VoiceChannel] = None, /, invoked = False):
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
            _.requester = ctx.author
            if not invoked:
                await ctx.embed(description=f"Connected to {channel.mention}")
            self.bot.loop.create_task(self._play_next_or_disconnect(_, None, None))
            return
        except TimeoutError:
            return await ctx.error("Connecting timed out...")
        except ClientException:
            return await ctx.error("I am already connected to a channel!")
        except OpusNotLoaded:
            return await ctx.error("Sorry! I couldn't do that. Try again soon.")

    @command(name="play")
    async def _play(self, ctx: NexusContext, *, query: Query):
        """
        Play a song.
        
        This can be from spotify or youtube.
        """
        if not ctx.voice_client:
            await self._connect(ctx, invoked=True)

        if isinstance(query, wavelink.YouTubePlaylist):
            tracks = query.tracks
        elif isinstance(query, list):
            tracks = query
        else:
            tracks = [query]

        player: Player = self.bot.wavelink.get_player(ctx.guild)
        player.queue.extend(tracks)

        _ = f"`{codeblocksafe(tracks[0].title)}`" if len(tracks) == 1 else f"{len(tracks)} tracks"
        return await ctx.embed(description=f"Added {_} to the queue")


async def setup(bot: Nexus):
    await bot.add_cog(NewMusic(bot))
