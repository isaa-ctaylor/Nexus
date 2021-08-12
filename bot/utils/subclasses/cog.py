from discord.ext.commands import Cog as DiscordCog


class Cog(DiscordCog):
    def __init_subclass__(cls, emoji: str = None, hidden: bool = False) -> None:
        cls.hidden = hidden
        cls.emoji = emoji

    @property
    def doc(self) -> str:
        _ = self.description.split("\n", maxsplit=1)

        if len(_) > 1:
            return _[1]

        return _[0]
