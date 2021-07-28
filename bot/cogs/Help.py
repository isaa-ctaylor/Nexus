from discord.ext.commands import Cog
from discord.ext.commands.help import HelpCommand
from discord import Embed

from ..utils.subclasses.bot import Nexus


class NexusHelp(HelpCommand):
    def get_command_signature(self, c):
        return f"{self.context.clean_prefix}{c.qualified_name} {c.signature}"

    async def send_bot_help(self, mapping):
        embeds = []
        for cog, commands in mapping.items():
            signatures = [
                self.get_command_signature(c)
                for c in self.filter_commands(commands, sort=True)
            ]
            if signatures:
                embeds.append(
                    Embed(
                        title=getattr(cog, "qualified_name", "No category"),
                        description="\n".join(signatures),
                        colour=self.context.bot.config.data.colours.neutral,
                    )
                )


class Help(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot
        self._old_help_command = self.bot.help_command

        self.bot.help_command = NexusHelp()
        self.bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self._old_help_command


def setup(bot: Nexus):
    bot.add_cog(Help(bot))
