from traceback import format_exception
from discord.embeds import Embed
from discord.errors import Forbidden
from discord.ext import commands
from utils.subclasses.cog import Cog
from utils.subclasses.bot import Nexus
from utils.subclasses.context import NexusContext


class Errors(Cog, hidden=True):
    def __init__(self, bot: Nexus):
        self.bot = bot

    async def _error(self, ctx: NexusContext, message: str):
        try:
            await ctx.paginate(
                Embed(
                    title="Error!",
                    description=f"```\n{message}```",
                    colour=self.bot.config.data.colours.bad,
                )
            )
        except Forbidden:
            await ctx.paginate(message)

    @Cog.listener(name="on_command_error")
    async def _handle_command_error(
        self, ctx: NexusContext, error: commands.CommandError
    ):
        if (
            ctx.command
            and ctx.command.has_error_handler()
            or ctx.cog
            and ctx.cog.has_error_handler()
        ):
            return

        ignored = (commands.CommandNotFound,)

        error = getattr(error, "original", error)

        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.MissingRequiredArgument):
            return await self._error(
                ctx,
                f"Whoops! Looks like you missed the {error.param.name} parameter!",
            )

        elif isinstance(error, commands.PrivateMessageOnly):
            return await self._error(
                ctx,
                "This command can only be used in a private message!",
            )

        elif isinstance(error, commands.NoPrivateMessage):
            return await self._error(
                ctx,
                "This command cannot be used in a private message!",
            )

        elif isinstance(error, commands.DisabledCommand):
            return await self._error(
                ctx,
                "This command is currently disabled! Sorry!",
            )

        elif isinstance(error, commands.TooManyArguments):
            return await self._error(
                ctx,
                f"Too many arguments passed to {ctx.invoked_with}",
            )

        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.message.author.id == self.bot.owner_id:
                await ctx.reinvoke()
                return
            return await self._error(
                ctx,
                f"You are on cooldown! Try again in {humanise.precisedelta(dt.timedelta(seconds=error.retry_after))}",
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            return await self._error(
                ctx,
                f"This command has reached maximum concurrency!",
            )

        elif isinstance(error, commands.NotOwner):
            return await self._error(
                ctx,
                "You need to be owner to execute this command!",
            )

        elif isinstance(error, commands.MessageNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the message {error.argument}!",
            )

        elif isinstance(error, commands.MemberNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the member {error.argument}!",
            )

        elif isinstance(error, commands.GuildNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the guild {error.argument}!",
            )

        elif isinstance(error, commands.UserNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the user {error.argument}!",
            )

        elif isinstance(error, commands.ChannelNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the channel {error.argument}!",
            )

        elif isinstance(error, commands.ChannelNotReadable):
            return await self._error(
                ctx,
                f"I can't read the channel {error.argument.name}!",
            )

        elif isinstance(error, commands.BadColourArgument):
            return await self._error(
                ctx,
                f"Unrecognised colour {error.argument}",
            )

        elif isinstance(error, commands.RoleNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the role {error.argument}!",
            )

        elif isinstance(error, commands.BadInviteArgument):
            return await self._error(
                ctx,
                f"That invite is invalid or expired!",
            )

        elif isinstance(error, commands.EmojiNotFound):
            return await self._error(
                ctx,
                f"Couldn't find the emoji {error.argument}!",
            )

        elif isinstance(error, commands.PartialEmojiConversionFailure):
            return await self._error(
                ctx,
                f"Invalid emoji {error.argument}!",
            )

        elif isinstance(error, commands.BadBoolArgument):
            return await self._error(
                ctx,
                f"Invalid bool argument!",
            )

        elif isinstance(error, commands.MissingPermissions):
            return await self._error(
                ctx,
                f"You are missing the following permissions: {', '.join([permission.replace('_', ' ').capitalize() for permission in error.missing_permissions])}",
            )

        elif isinstance(error, commands.BotMissingPermissions):
            return await self._error(
                ctx,
                f"I am missing the following permissions: {', '.join([permission.replace('_', ' ').capitalize() for permission in error.missing_permissions])}",
            )

        elif isinstance(error, commands.MissingRole):
            return await self._error(
                ctx,
                f"You dont have the role {error.missing_role if isinstance(role, str) else (await ctx.guild.fetch_role(error.missing_role)).name}!",
            )

        elif isinstance(error, commands.BotMissingRole):
            return await self._error(
                ctx,
                f"I dont have the role {error.missing_role if isinstance(role, str) else (await ctx.guild.fetch_role(error.missing_role)).name}!",
            )

        elif isinstance(error, commands.MissingAnyRole):
            missing_roles = ", ".join(
                [
                    (
                        (await ctx.guild.fetch_role(role)).name
                        if ctx.guild.get_role(role) is None
                        else ctx.guild.get_role(role)
                    )
                    if isinstance(role, int)
                    else role
                    for role in error.missing_roles
                ]
            )
            return await self._error(
                ctx,
                f"You are missing the following roles: {missing_roles}!",
            )

        elif isinstance(error, commands.BotMissingAnyRole):
            missing_roles = ", ".join(
                [
                    (
                        (await ctx.guild.fetch_role(role)).name
                        if ctx.guild.get_role(role) is None
                        else ctx.guild.get_role(role)
                    )
                    if isinstance(role, int)
                    else role
                    for role in error.missing_roles
                ]
            )
            return await self._error(
                ctx,
                f"I am missing the following roles: {missing_roles}!",
            )

        elif isinstance(error, commands.NSFWChannelRequired):
            return await self._error(
                ctx,
                f'The channel "{error.channel.name}" needs to be marked NSFW!',
            )

        elif isinstance(error, commands.BadArgument):
            return await self._error(
                ctx,
                error.args[0],
            )

        else:
            channel = self.bot.get_channel(self.bot.config.data.channels.errors)
            message = (
                f"**Server:** {ctx.guild.name}\n"
                f"**Invoker:** {ctx.author}\n"
                f"**Message content (max 100 characters):** {ctx.message.content[:100]}\n"
                f"**Traceback:**\n```py\n{''.join(format_exception(type(error), error, error.__traceback__))}```"
            )

            if len(message) > 4069:
                message = message[:4057], "[TRUNCATED]"

            await channel.send(
                embed=Embed(
                    title="Error!",
                    description=message,
                    colour=self.bot.config.data.colours.bad,
                )
            )


def setup(bot: Nexus):
    bot.add_cog(Errors(bot))
