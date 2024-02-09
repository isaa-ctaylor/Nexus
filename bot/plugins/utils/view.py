import discord
import typing
from .embed import NeutralEmbed, SuccessEmbed


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None
        self.interaction = None
        
    def disable_children(self):
        for c in self.children:
            c.disabled = True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.disable_children()
        self.interaction = interaction
        self.value = True
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.disable_children()
        await interaction.response.edit_message(
            embed=NeutralEmbed("Cancelled"), view=self
        )

        self.value = False
        self.stop()
