import re
from os import getenv
from typing import Optional, Union

import async_timeout
import wavelink
from discord import ClientException, TextChannel, VoiceChannel, VoiceProtocol
from discord.ext.commands import Converter
from discord.opus import OpusNotLoaded
from utils import codeblocksafe
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import command
from utils.subclasses.context import NexusContext
from wavelink.ext import spotify

SPOTIFY = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)
SPOTIFY_REQUEST = "https://api.spotify.com/v1/{type}s/{id}"


class Player(wavelink.Player):
    control_channel: TextChannel


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
        elif _ := await wavelink.YouTubePlaylist.convert(ctx, argument):
            return _
        elif _ := await wavelink.YouTubeTrack.convert(ctx, argument):
            return _
        elif _ := await wavelink.YouTubeMusicTrack.convert(ctx, argument):
            return _


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
    @Cog.listener(name="on_wavelink_track_exception")
    async def _play_next_or_disconnect(self, player: Player, track: wavelink.Track, _):
        await player.control_channel.send("a")
        try:
            with async_timeout.timeout(300): # 5 minutes
                track = await player.queue.get_wait()
                await player.play(track)
                await player.control_channel.send(f"Now playing: `{codeblocksafe(track.title)}`")
        except TimeoutError:
            await player.disconnect()

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
            self.bot.wavelink._players.append(_)
            if not invoked:
                await ctx.embed(description=f"Connected to {channel.mention}")
            await self._play_next_or_disconnect(_, None, None)
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
