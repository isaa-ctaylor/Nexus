from typing import Optional

from discord import VoiceChannel, ClientException
from discord.opus import OpusNotLoaded
from utils.subclasses.command import command
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext
import wavelink


class NewMusic(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        
        self.bot.loop.create_task(self._connect_node())
    
    async def _connect_node(self):
        await self.bot.wait_until_ready()

        if not getattr(self.bot, "wavelink", None):
            self.bot.wavelink = wavelink.NodePool.create_node(bot=self.bot, host="127.0.0.1", port=2333, password="youshallnotpass")
        
    @command(name="connect", aliases=["join"])
    async def _connect(self, ctx: NexusContext, channel: Optional[VoiceChannel] = None):
        """
        Connect Nexus to a voice channel
        """
        if not channel:
            if vc := ctx.voice_client:
                if vc.channel.id == channel.id:
                    return await ctx.error(f"Already connected to {channel.name}!")
                if not ctx.author.guild_permissions.manage_guild:
                    return await ctx.error(f"I am already connected to a channel! ({channel.name})")

        try:
            await channel.connect()
            await ctx.embed(description=f"Connected to {channel.mention}")
        except TimeoutError:
            return await ctx.error("Connecting timed out...")
        except ClientException:
            return await ctx.error("I am already connected to a channel!")
        except OpusNotLoaded:
            return await ctx.error("Sorry! I couldn't do that. Try again soon.")

def setup(bot: Nexus):
    bot.add_cog(NewMusic(bot))