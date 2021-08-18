from io import BytesIO
from discord.file import File
from pytube.query import StreamQuery
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import Group, group
from utils.subclasses.context import NexusContext
from pytube import YouTube
from pytube.exceptions import RegexMatchError


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
        try:
            streams = YouTube(url).streams

        except RegexMatchError:
            return await ctx.error("Invalid link!")

        streams.filter(only_audio=True, file_extension="mp3")

        if not streams.count():
            return await ctx.error("Couldn't download that video in mp3 format!")

        video = streams.desc().first()

        b = BytesIO()
        video.stream_to_buffer(b)
        b.seek(0)

        return await ctx.reply(file=File(b))


def setup(bot: Nexus):
    bot.add_cog(Utility(bot))
