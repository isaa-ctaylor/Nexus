import asyncio
import asyncpg
import logging
import typing
import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Cog
from subclasses.bot import Bot

from .utils.transformer import DatetimeTransformer
from .utils.embed import ErrorEmbed, SuccessEmbed, NeutralEmbed
from .utils import hyperlink


UTC_ADJUST = 86400  # TODO: Detect automagically


class ReminderException(app_commands.AppCommandError):
    """Base class for reminder exceptions"""


class ReminderDoesntExist(ReminderException):
    """No reminder with that id!"""


class NoReminders(ReminderException):
    """You do not have any reminders set!"""


class Reminder(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.logger = logging.getLogger("discord.bot.plugins.Reminder")

        self._reminder_loop.start()

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, discord.app_commands.CommandInvokeError):
            error = error.original

        if isinstance(
            error,
            (ReminderDoesntExist, NoReminders),
        ):
            message = error.__doc__

        if isinstance(error, app_commands.errors.TransformerError):
            message = "Failed to convert your input to something meaningful...\nPlease try again."

        else:
            message = f"An error occured. If the issue persists, please contact the support team."
            self.logger.error(
                str(error), exc_info=(type(error), error, error.__traceback__)
            )

        embed = ErrorEmbed(message)

        try:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.InteractionResponded:
            await interaction.followup.send(embed=embed, ephemeral=True)

    reminder = app_commands.Group(name="reminder", description="Reminders")

    @tasks.loop(minutes=1)
    async def _reminder_loop(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        due_before = now + datetime.timedelta(minutes=1)

        reminders = await self.bot.database.fetch(
            "SELECT * FROM reminder WHERE due < $1", due_before
        )

        for reminder in reminders:
            await self._execute_reminder(now, reminder)

    @commands.Cog.listener(name="on_reminder_created")
    async def _on_reminder_created(self, reminder: asyncpg.protocol.Record) -> None:
        now = datetime.datetime.now(datetime.timezone.utc)
        sleep = (reminder["due"] - now).seconds

        if sleep < 60:
            await self._execute_reminder(now, reminder)

    async def _execute_reminder(
        self, now: datetime.datetime, reminder: asyncpg.protocol.Record
    ) -> None:
        await self.bot.wait_until_ready()
        sleep = (reminder["due"] - now).seconds

        await asyncio.sleep(sleep)

        channel: typing.Optional[
            typing.Union[discord.TextChannel, discord.VoiceChannel]
        ] = await self.bot.fetch_channel(reminder["channel"])

        if channel:
            owner: typing.Optional[discord.Member] = await channel.guild.fetch_member(
                reminder["member"]
            )
            if owner:
                await channel.send(
                    f"{owner.mention}, {discord.utils.format_dt(reminder['created'], 'R')}\n{reminder['reason']}"
                )
                await self.bot.database.execute(
                    "DELETE FROM reminder WHERE id = $1", reminder["id"]
                )

    @reminder.command(name="create")
    async def _reminder_create(
        self,
        interaction: discord.Interaction,
        datetime: app_commands.Transform[datetime.datetime, DatetimeTransformer],
        message: str,
    ) -> None:
        """Create a reminder

        :param interaction: Interaction created by discord
        :type interaction: discord.Interaction
        :param datetime: When to remind
        :type datetime: app_commands.Transform[datetime.datetime, DatetimeTransformer]
        :param message: Message to remind you
        :type message: typing.Optional[str]
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        await self.bot.ensure_user(interaction.user.id)

        r = await self.bot.database.fetchrow(
            "INSERT INTO reminder (member, reason, channel, created, due) VALUES ($1, $2, $3, $4, $5) RETURNING *",
            interaction.user.id,
            message,
            interaction.channel_id,
            interaction.created_at,
            datetime,
        )

        await interaction.followup.send(
            f"Ok, {discord.utils.format_dt(r['due'], 'R')}: {r['reason']} (ID: `{r['id']}`)",
            ephemeral=True,
        )

        self.bot.dispatch("reminder_created", r)

    @reminder.command(name="delete")
    async def _reminder_delete(self, interaction: discord.Interaction, id: int) -> None:
        """Delete a reminder

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        :param id: Reminder id
        :type id: int
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        r = await self.bot.database.fetchrow(
            "DELETE FROM reminder WHERE id = $1 AND member = $2 RETURNING *",
            id,
            interaction.user.id,
        )
        if not r:
            raise ReminderDoesntExist
        else:
            await interaction.followup.send(
                embed=SuccessEmbed(f"Deleted reminder {r['id']} ({r['reason']})"),
                ephemeral=True,
            )

    @reminder.command(name="list")
    async def _reminder_list(self, interaction: discord.Interaction) -> None:
        """List currently set reminders

        :param interaction: Interaction provided by discord
        :type interaction: discord.Interaction
        """
        await interaction.response.defer(thinking=True, ephemeral=True)
        reminders = await self.bot.database.fetch(
            "SELECT id, reason, due FROM reminder WHERE member = $1",
            interaction.user.id,
        )
        if not reminders:
            raise NoReminders
        else:
            embed = NeutralEmbed(
                title=f"{len(reminders)} reminder{'s' if len(reminders) != 1 else ''} set"
            )
            lines = []

            for r in reminders:
                lines.append(
                    f"{discord.utils.format_dt(r['due'], 'R')}) {r['reason']} (ID: `{r['id']}`)"
                )
                if len("\n".join(lines)) > 4096:
                    lines.pop()
                    break

            embed.description = "\n".join(lines)

            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: Bot):
    await bot.add_cog(Reminder(bot))
