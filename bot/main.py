from discord.ext.commands.bot import when_mentioned_or
from utils.subclasses.bot import Nexus

Nexus(command_prefix=when_mentioned_or("Nxs")).run()
