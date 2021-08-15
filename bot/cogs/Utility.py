from asyncio.subprocess import create_subprocess_shell
from os import path, remove
from pathlib import Path

from discord.file import File
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Group, group
from utils.subclasses.context import NexusContext
from youtube_dl import YoutubeDL

PATH = path.join(path.dirname(__file__), "./output/")
RETRY = 5


class Utility(Cog):
    def __init__(self, bot: Nexus):
        self.bot = bot

    @group(name="download", cls=Group)
    async def _download(self, ctx: NexusContext, url: str):
        """
        Download a file from youtube

        Defaults to audio, video can be done through the download video command
        """
        if not ctx.invoked_subcommand:
            await self._download_audio(ctx, url)

    @_download.command(name="audio")
    async def _download_audio(self, ctx: NexusContext, url: str):
        """
        Download audio from the given url
        """
        ytdl = YoutubeDL(
            {"quiet": True, "format": "mp4", "outtmpl": f"{PATH}%(id)s.%(ext)s"}
        )

        p = Path(PATH)

        for _ in range(RETRY):
            try:
                data = ytdl.extract_info(url)

                filename = str(p.glob(f"{data['id']}.*")[0])

                create_subprocess_shell(
                    f"ffmpeg -i {filename} -acodec libmp3lame {PATH}{data['id']}.mp3"
                )

                remove(filename)
            except:
                continue

        if Path(f"{PATH}{data['id']}.mp3").exists():
            await ctx.paginate(File(f"{PATH}{data['id']}.mp3"))

        else:
            await ctx.error("Failed to download!")


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
