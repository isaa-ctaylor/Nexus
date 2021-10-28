from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.bot import Nexus


class Music(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot


def setup(bot: Nexus):
    bot.add_cog(Music(bot))
