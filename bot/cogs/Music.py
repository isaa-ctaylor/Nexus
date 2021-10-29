from os import getenv
from typing import Optional, Union

from discord.channel import VoiceChannel
from discord.errors import ClientException
from discord.ext.commands.core import guild_only
from dotenv import load_dotenv
from wavelink.tracks import SoundCloudTrack
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.context import NexusContext
from wavelink import Node, NodePool, Player, YouTubeTrack
from wavelink.ext.spotify import SpotifyClient, SpotifyRequestError, SpotifyTrack
from discord.ext.commands import command

load_dotenv()


class Music(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

        bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """
        Connect to our Lavalink nodes.
        """
        await self.bot.wait_until_ready()

        await NodePool.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port=2333,
            password="youshallnotpass",
            spotify_client=SpotifyClient(
                client_id=getenv("SPOTIFY_ID"), client_secret=getenv("SPOTIFY_SECRET")
            ),
        )

    @Cog.listener(name="on_wavelink_node_ready")
    async def _log_node_ready(self, node: Node):
        """
        Event fired when a node has finished connecting.
        """
        self.bot.logger.info(f"Node: <{node.identifier}> is ready!")

    @guild_only()
    @command(cls=Command, name="connect", aliases=["join"])
    async def _connect(self, ctx: NexusContext, *, channel: Optional[VoiceChannel] = None, invoked=False):
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
                if not invoked:
                    await ctx.embed(title="Done!", description=f"Joined {channel.mention}", colour=self.bot.config.colours.good)
                else:
                    await ctx.reply(f"Joined {channel.mention}")
            except:
                return await ctx.error("Uh oh! I couldn't join, please")
            
    @guild_only()
    @command(cls=Command, name="play")
    async def _play(self, ctx: NexusContext, *, query: str):
        """
        Play a song from Youtube
        """
        _ = False
        if not ctx.voice_client:
            _ = True
            await self._connect(ctx, invoked=True)
            
        __ = ctx.send if _ else ctx.reply
        
        await __(f"Searching {query}")
        
        
        track = None
        try:
            track = await SpotifyTrack.convert(ctx, query)
        except SpotifyRequestError:
            pass
        
        if track is None:
            try:
                track = await YouTubeTrack.convert(ctx, query)
            except Exception as e:
                await ctx.send(e)

def setup(bot: Nexus):
    bot.add_cog(Music(bot))
