from os import getenv
from typing import Optional

from discord.channel import VoiceChannel
from discord.ext.commands.core import guild_only
from dotenv import load_dotenv
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.context import NexusContext
from wavelink import Node, NodePool, Player, YouTubeTrack
from wavelink.ext import spotify
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
            spotify_client=spotify.SpotifyClient(
                client_id=getenv("SPOTIFY_ID"),
                client_secret=getenv("SPOTIFY_SECRET")
            )
        )

    @Cog.listener(name="on_wavelink_node_ready")
    async def _log_node_ready(self, node: Node):
        """
        Event fired when a node has finished connecting.
        """
        self.bot.logger.info(f"Node: <{node.identifier}> is ready!")

    @guild_only()
    @command(cls=Command, name="connect")
    async def _connect(self, ctx: NexusContext, channel: Optional[VoiceChannel] = None):
        """
        Connect to a voice channel
        
        Defaults to your current channel if not specified
        """
        if (
            ctx.voice_client
            and len(ctx.voice_client.channel.members) > 1
            and (
                len(ctx.voice_client.channel.members) != 2
                or ctx.author.id
                not in [m.id for m in ctx.voice_client.channel.members]
            )
        ):
            return await ctx.error("I am already connected to a voice channel!")

        try:
            channel = channel or ctx.author.voice.channel
        except AttributeError:
            return await ctx.error("Please specify a channel or join one!")

        await channel.connect(cls=Player)
                


def setup(bot: Nexus):
    bot.add_cog(Music(bot))
