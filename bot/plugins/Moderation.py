import typing
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from subclasses.bot import Bot
from discord import app_commands

class Moderation(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="ban")
    async def _ban(self, interaction: discord.Interaction, member: discord.User, reason: typing.Optional[str]) -> None:
        """Ban someone

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param member: Member to ban
        :type member: discord.User
        :param reason: Ban reason
        :type reason: typing.Optional[str]
        """
        await interaction.response.send_message(f"{member} {reason}")

async def setup(bot: Bot):
    await bot.add_cog(Moderation(bot))