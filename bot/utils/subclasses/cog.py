from discord.ext.commands import Cog as DiscordCog


class Cog(DiscordCog):
    def __init_subclass__(cls, hidden: bool = False) -> None:
        cls.hidden = hidden

    @property
    def doc(self) -> str:
        _ = self.description.split("\n", maxsplit=1)

        if len(_) > 1:
            return _[1]

        return _[0]
