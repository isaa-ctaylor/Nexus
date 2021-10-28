from discord.embeds import Embed
from discord.ext.commands.core import command
from discord.member import Member
from discord.reaction import Reaction
from utils.games.player import Player
from utils.games.tictactoe import TicTacToe
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Command
from utils.subclasses.context import NexusContext
import asyncio


class Games(Cog):
    """
    Fun minigames to play with friends
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

    @command(name="tictactoe", cls=Command, aliases=["ttt"])
    async def _tictactoe(self, ctx: NexusContext, player: Member):
        if ctx.interaction:
            await ctx.interaction.response.defer()

        ttt = TicTacToe(
            players=(
                Player("❌", identifier=str(ctx.author)),
                Player("⭕"),
            )
        )

        embed = Embed(
            title="Tic Tac Toe",
            description=ttt.render(),
            colour=self.bot.config.colours.neutral,
        )

        _msg = await ctx.send(embed=embed)

        emojimap = {str(i) + "\N{COMBINING ENCLOSING KEYCAP}": i for i in range(1, 10)}

        for e in emojimap:
            await _msg.add_reaction(e)

        def check(r: Reaction, u: Member):
            return u.id == ctx.author.id and r.message.id == _msg.id and r.emoji in emojimap

        while True:
            try:
                r, u = await self.bot.wait_for("reaction_add", check=check, timeout=30)
            except asyncio.TimeoutError:
                return await ctx.error("You didn't play in time!")
            
            ttt.place(emojimap[u.emoji])
            await _msg.edit(embed=Embed(title="Tic Tac Toe",
            description=ttt.place(),
            colour=self.bot.config.colours.neutral)
