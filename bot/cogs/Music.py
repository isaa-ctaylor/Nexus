import asyncio
from asyncio import Queue
from os import getenv
from typing import Optional

from discord.channel import TextChannel, VoiceChannel
from discord.client import Client
from discord.embeds import Embed
from discord.ext.commands import command
from discord.ext.commands.core import guild_only
from discord.ext.commands.errors import BadArgument
from discord.mentions import AllowedMentions
from dotenv import load_dotenv
from utils import codeblocksafe, hyperlink
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.context import NexusContext
from wavelink import Node, NodePool, Player, YouTubeTrack
from wavelink.ext.spotify import SpotifyClient, SpotifyRequestError, SpotifyTrack
from wavelink.tracks import SoundCloudTrack, Track
from wavelink.utils import MISSING
import async_timeout
import math
from typing import Union
import pomice

load_dotenv()


class Player(pomice.Player):
    def __init__(
        self,
        client: Client = MISSING,
        channel: VoiceChannel = MISSING,
        *,
        node: pomice.Node = MISSING,
    ):
        self.control_channel: TextChannel = None
        super().__init__(client=client, channel=channel, node=node)
        self.queue = Queue()
        self.skippers = set()


class Music(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

        if not hasattr(self.bot, "pomice"):
            self.bot.pomice = pomice.NodePool()

        bot.loop.create_task(self.connect_nodes())

    def required(self, ctx: NexusContext):
        player: Player = ctx.voice_client
        channel = self.bot.get_channel(int(player.channel.id))
        return math.ceil((len(channel.members) - 1) / 2.5)

    async def connect_nodes(self):
        """
        Connect to our Lavalink nodes.
        """
        await self.bot.wait_until_ready()

        await self.bot.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port=2333,
            password="youshallnotpass",
            spotify_client_id=getenv("SPOTIFY_ID"),
            spotify_client_secret=getenv("SPOTIFY_SECRET")
        )

    @Cog.listener(name="on_pomice_track_end")
    async def _do_next_song(
        self, event: pomice.PomiceEvent, player: Player, track: pomice.Track, reason
    ):
        if reason not in ["FINISHED", "STOPPED", "SKIPPED"]:
            return

        if reason == "SKIPPED":
            await player.stop()

        try:
            with async_timeout.timeout(300):
                track = await player.queue.get()
            await player.play(track)
            return await player.control_channel.send(
                f"Now playing `{track.title}` | {track.requester.mention}",
                allowed_mentions=AllowedMentions.none(),
            )
        except asyncio.TimeoutError:
            await player.disconnect(force=True)
            return await player.control_channel.send("👋 Disconnected - queue finished")

    @guild_only()
    @command(cls=Command, name="connect", aliases=["join"])
    async def _connect(
        self,
        ctx: NexusContext,
        *,
        channel: Optional[VoiceChannel] = None,
        invoked=False,
    ):
        """
        Connect to a voice channel

        Defaults to your current channel if not specified
        """
        if (
            ctx.voice_client
            and len(ctx.voice_client.channel.members) > 1
            and (
                len(ctx.voice_client.channel.members) != 2
                or ctx.author.id not in [m.id for m in ctx.voice_client.channel.members]
            )
        ):
            return await ctx.error("I am already connected to a voice channel!")

        try:
            channel = channel or ctx.author.voice.channel
        except AttributeError:
            return await ctx.error("Please specify a channel or join one!")

        if ctx.voice_client and channel.id == ctx.voice_client.channel.id:
            return await ctx.error("I am already connected to that channel!")

        if ctx.voice_client and not ctx.author.voice:
            return await ctx.error("Please join a channel in order to connect me!")

        if (
            ctx.voice_client
            and ctx.author.voice
            and (
                (len(ctx.voice_client.channel.members) == 1)
                or (
                    len(ctx.voice_client.channel.members) == 2
                    and ctx.voice_client.channel.id == ctx.author.voice.channel.id
                )
            )
        ):
            await ctx.voice_client.move_to(channel)

        else:
            if not channel.permissions_for(ctx.guild.me).connect:
                return await ctx.error("I do not have permission to join that channel!")
            try:
                await channel.connect(cls=Player)
                ctx.voice_client.control_channel = ctx.channel
                if not invoked:
                    await ctx.embed(
                        title="Done!",
                        description=f"Joined {channel.mention}",
                        colour=self.bot.config.colours.good,
                    )
                else:
                    await ctx.reply(f"Joined {channel.mention}")
            except Exception as e:
                return await ctx.error(
                    f"Uh oh! I couldn't join, please try again later\n\nError: {type(e)}: {e}"
                )

    @guild_only()
    @command(cls=Command, name="play")
    async def _play(self, ctx: NexusContext, *, query: str):
        """
        Play a song from Youtube
        """
        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if (
            ctx.voice_client
            and ctx.author.voice.channel.id != ctx.voice_client.channel.id
        ):
            return await ctx.error("You are not in the same channel as me!")

        _ = False
        if not ctx.voice_client:
            _ = True
            await self._connect(ctx, invoked=True)

        if _:
            await ctx.send(f"🔍 Searching for `{codeblocksafe(query)}`")
        else:
            await ctx.reply(
                f"🔍 Searching for `{codeblocksafe(query)}`", mention_author=False
            )

        player: Player = ctx.voice_client
        tracks = await player.get_tracks(query=query, ctx=ctx)

        if not tracks:
            await ctx.send("❌ No results!")

        if isinstance(tracks, pomice.Playlist):
            await ctx.send(f"Adding {tracks.track_count} songs to the queue")

            for track in tracks.tracks:
                track.requester = ctx.author
                await player.queue.put(track)

            if not player.is_playing and not player.is_paused:
                await player.play(player.queue.get_nowait(), ignore_if_playing=True)

            else:
                await player.control_channel.send(
                    f"Enqueued {tracks.track_count} songs."
                )

        else:
            tracks[0].requester = ctx.author
            if not player.is_playing and not player.is_paused:
                await player.play(tracks[0])
                await ctx.send(f"Playing `{codeblocksafe(tracks[0].title)}`")

            else:
                await player.queue.put(tracks[0])
                await ctx.send(f"Enqueued `{codeblocksafe(tracks[0].title)}`")

    @guild_only()
    @command(cls=Command, name="stop")
    async def _stop(self, ctx: NexusContext):
        """
        Stops the player and clears the queue
        """
        if not ctx.voice_client:
            return await ctx.error("I am not playing anything at the moment!")

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        player: Player = ctx.voice_client

        await player.stop()
        player.queue._queue.clear()
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(cls=Command, name="leave")
    async def _leave(self, ctx: NexusContext):
        """
        Leave the current voice channel
        """
        if not ctx.voice_client:
            return await ctx.error("I am not playing anything at the moment!")

        if (
            ctx.author.voice
            and ctx.author.voice.channel.id != ctx.voice_client.channel.id
        ):
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        player: Player = ctx.voice_client

        await player.destroy()
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(cls=Command, name="queue")
    async def _queue(self, ctx: NexusContext):
        """
        See the current queue
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        pages = [
            list(player.queue._queue)[i : i + 10]
            for i in range(0, len(player.queue._queue), 10)
        ]

        embeds = [
            Embed(
                description="\n".join(
                    f"{list(player.queue._queue).index(t) + 1}) {hyperlink(f'`{t.title}`', t.uri)}"
                    for t in l
                ),
                colour=self.bot.config.colours.neutral,
            )
            for l in pages
        ]

        embeds[0].description = (
            f"**Now playing**: {hyperlink(player.current.title, player.current.uri)}\n\n"
            + embeds[0].description.strip()
        )

        if thumb := getattr(player.current, "thumbnail", None):
            embeds[0].set_thumbnail(url=thumb)

        await ctx.paginate(embeds)

    @guild_only()
    @command(cls=Command, name="remove")
    async def _remove(self, ctx: NexusContext, index: int):
        """
        Remove a song from the queue
        """
        player: Player = ctx.voice_client
        
        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if (
            ctx.author.voice
            and ctx.author.voice.channel.id != player.channel.id
        ):
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        try:
            track: Track = list(player.queue._queue)[index - 1]
        except IndexError:
            return await ctx.error("Please provide a valid song index!")

        if track.requester.id != ctx.author.id:
            return await ctx.error("You did not request this song!")

        player.queue._queue.remove(track)
        await ctx.reply(
            f"👍 Removed `{track.title}` from the queue", mention_author=False
        )

    @guild_only()
    @command(cls=Command, name="pause")
    async def _pause(self, ctx: NexusContext):
        """
        Pause the current song
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if (
            ctx.author.voice
            and ctx.author.voice.channel.id != player.channel.id
        ):
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if player.is_paused:
            return await ctx.error("The player is already paused!")

        await player.set_pause(True)
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(cls=Command, name="resume")
    async def _resume(self, ctx: NexusContext):
        """
        Resume the paused song
        """
        player: Player = ctx.voice_client
        
        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if (
            ctx.author.voice
            and ctx.author.voice.channel.id != player.channel.id
        ):
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if not player.is_paused():
            return await ctx.error("The player is not paused!")

        await player.set_pause(False)
        await ctx.message.add_reaction("👍")

    @guild_only()
    @command(cls=Command, name="now")
    async def _now(self, ctx: NexusContext):
        """
        See what song is currently playing
        """
        player: Player = ctx.voice_client
        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        await ctx.embed(
            title="Currently playing",
            description=f"{hyperlink(f'`{player.current.title}`', player.current.uri)} requested by {player.current.requester.mention}",
        )

    @guild_only()
    @command(cls=Command, name="skip")
    async def _skip(self, ctx: NexusContext):
        """
        Skip the current song
        """
        player: Player = ctx.voice_client
        
        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if (
            ctx.author.voice
            and ctx.author.voice.channel.id != player.channel.id
        ):
            return await ctx.error("You are not in the same channel as me!")

        if not ctx.author.voice:
            return await ctx.error("You are not in a voice channel!")

        if (
            ctx.author.id != player.current.requester.id
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

        await ctx.send("⏭ Skipping")

        self.bot.dispatch(
            "pomice_track_end", ctx.voice_client, ctx.voice_client.track, "SKIPPED"
        )

    @guild_only()
    @command(cls=Command, name="volume")
    async def _volume(self, ctx: NexusContext, volume: Union[int, str]):
        """
        Set the volume of the player
        """
        player: Player = ctx.voice_client

        if not player:
            return await ctx.error("I am not playing anything at the moment!")

        if (
            ctx.author.voice
            and ctx.author.voice.channel.id != player.channel.id
        ):
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

        player.set_volume(volume)
        await ctx.message.add_reaction("👍")


def setup(bot: Nexus):
    bot.add_cog(Music(bot))
