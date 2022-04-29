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
            self.bot.wavelink = wavelink.NodePool.create_node(bot=self.bot, host="127.0.0.1", password="youshallnotpass")
        

def setup(bot: Nexus):
    bot.add_cog(NewMusic(bot))