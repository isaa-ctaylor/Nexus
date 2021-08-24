from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus


class Utility(Cog):
    def __init__(self, bot: Nexus):
        self.bot = Nexus



def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
