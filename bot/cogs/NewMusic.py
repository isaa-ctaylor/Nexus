from typing import Union
from os import getenv
import re
from typing import Optional

from discord import VoiceChannel, ClientException
from discord.ext.commands import Converter
from discord.opus import OpusNotLoaded
from utils.subclasses.command import command
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext
import wavelink
from wavelink.ext import spotify


SPOTIFY = re.compile(
    r"https?://open.spotify.com/(?P<type>album|playlist|track)/(?P<id>[a-zA-Z0-9]+)"
)
SPOTIFY_REQUEST = "https://api.spotify.com/v1/{type}s/{id}"


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
            await channel.connect(self_deaf=True, cls=wavelink.Player)
            if not invoked:
                await ctx.embed(description=f"Connected to {channel.mention}")
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
            await self._connect(ctx)

        if isinstance(query, wavelink.YouTubePlaylist):
            tracks = query.tracks
        elif isinstance(query, list):
            tracks = query
        else:
            tracks = [query]

        player: Player = self.bot.wavelink.get_player(ctx.guild.id)
        player.queue.extend(tracks)

        _ = f"`{tracks[0].title}`" if len(tracks) == 1 else f"{len(tracks)} tracks"
        return await ctx.embed(f"Added {_} to the queue")


async def setup(bot: Nexus):
    await bot.add_cog(NewMusic(bot))
