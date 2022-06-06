from random import choice
from utils.subclasses.command import command
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext
from utils.subclasses.cog import Cog


class Fun(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    @command(name="8ball")
    async def _8ball(self, ctx: NexusContext, *, question: str):
        return await ctx.embed(
            title=question.capitalize(),
            description=choice(
                [
                    "As I see it, yes.",
                    "Ask again later.",
                    "Better not tell you now.",
                    "Cannot predict now.",
                    "Concentrate and ask again.",
                    "Don't count on it.",
                    "It is certain.",
                    "It is decidedly so.",
                    "Most likely.",
                    "My reply is no.",
                    "My sources say no.",
                    "Outlook not so good.",
                    "Outlook good.",
                    "Reply hazy, try again.",
                    "Signs point to yes.",
                    "Very doubtful.",
                    "Without a doubt.",
                    "Yes.",
                    "Yes - definitely.",
                    "You may rely on it.",
                ]
            ),
        )



async def setup(bot: Nexus):
    await bot.add_cog(Fun(bot))
    
