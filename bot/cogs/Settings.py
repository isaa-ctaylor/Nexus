from typing import Any, Optional
from discord.channel import TextChannel
from discord.embeds import Embed
from discord.errors import Forbidden, HTTPException
from discord.ext.commands.converter import Converter
from discord.ext.commands.core import has_guild_permissions, bot_has_guild_permissions
from discord.member import Member
from discord.role import Role
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import group, command
from utils.subclasses.context import NexusContext
from utils import codeblocksafe
from tagformatter import Parser
from contextlib import suppress


class Prefix(Converter):
    async def convert(self, ctx: NexusContext, argument: Any):
        argument = str(argument)
        if argument.startswith('"') and argument.endswith('"'):
            return argument[1:-1]
        return argument


class Module(Converter):
    async def convert(self, ctx: NexusContext, argument: Any):
        if argument.lower().strip() == "all":
            return "all"

        if (arg := argument.strip().capitalize()) in list(ctx.bot.cogs):
            return arg

        return None


class Toggle(Converter):
    async def convert(self, ctx: NexusContext, argument: Any):
        if argument.lower().strip() in ["enable", "on", "yes", "enabled"]:
            return True

        if argument.lower().strip() in ["disable", "disabled", "no", "off"]:
            return False


class Settings(Cog):
    """
    Settings for your server
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

        self.bot.loop.create_task(self.__ainit__())

        self.parser = Parser()

        @self.parser.tag("member")
        def member(env):
            return str(env.member)

        @member.tag("mention")
        def member_mention(env):
            return env.member.mention

        @member.tag("name")
        def member_name(env):
            return env.member.name

        @member.tag("id")
        def member_id(env):
            return env.member.id

        @member.tag("discriminator")
        def member_discriminator(env):
            return env.member.discriminator

        @member.tag("full_name")
        def member_full_name(env):
            return str(env.member)

        @self.parser.tag("server")
        def server(env):
            return str(env.server)

        @server.tag("name")
        def server_name(env):
            return env.server.name

        @server.tag("id")
        def server_id(env):
            return env.server.id

    async def __ainit__(self):
        data = await self.bot.db.fetch("SELECT * FROM welcome", one=False)

        self._welcome_cache = {
            record["guild_id"]: {
                "enabled": record["enabled"],
                "channel": self.bot.get_channel(record["channel"]),
                "message": record["message"],
                "role": record["role"],
            }
            for record in data
        }

    @command(name="prefix")
    async def _prefix(self, ctx: NexusContext, prefix: Optional[Prefix] = None):
        """
        Change/see the current prefix(es)

        You need Manage Messages server perms to change the prefix
        """
        if not prefix:
            prefix = self.bot.prefixes.get(ctx.guild.id, ["Nxs"])[0]

            return await ctx.paginate(
                Embed(
                    title="Prefix",
                    description=f"```\nThe prefix for {codeblocksafe(ctx.guild.name)} is {codeblocksafe(prefix)}```",
                    colour=self.bot.config.colours.neutral,
                )
            )

        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.error(
                "You do not have the Manage Messages server permission!"
            )

        if ctx.guild.id not in self.bot.prefixes:
            await self.bot.db.execute(
                "INSERT INTO prefixes VALUES($1, $2)", ctx.guild.id, [prefix]
            )
            self.bot.prefixes[ctx.guild.id] = [prefix]

        else:
            await self.bot.db.execute(
                "UPDATE prefixes SET prefixes = $1 WHERE guild_id = $2",
                [prefix],
                ctx.guild.id,
            )

        await ctx.embed(
            title="Done!",
            description=f"```\nSet the prefix to {codeblocksafe(prefix)}```",
            colour=self.bot.config.colours.good,
        )

        self.bot.prefixes = {
            r["guild_id"]: r["prefixes"]
            for r in [
                dict(r)
                for r in await self.bot.db.fetch("SELECT * FROM prefixes", one=False)
            ]
        }

    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_roles=True)
    @group(name="welcome", invoke_without_command=True)
    async def _welcome(self, ctx: NexusContext):
        """
        Welcome message settings

        Functionality within the subcommands
        """
        if not ctx.invoked_subcommand:
            return await ctx.send_help(ctx.command)

    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_roles=True)
    @_welcome.command(name="enable")
    async def _welcome_enable(self, ctx: NexusContext):
        """
        Enables the welcome message
        """
        _ = False
        if ctx.guild.id in self._welcome_cache:
            if self._welcome_cache[ctx.guild.id]["enabled"]:
                return await ctx.error("Welcome messages are already enabled!")

            await self.bot.db.execute(
                "UPDATE welcome SET enabled = $1 WHERE guild_id = $2",
                True,
                ctx.guild.id,
            )
        else:
            _ = True
            await self.bot.db.execute(
                "INSERT INTO welcome (guild_id, message, enabled) VALUES ($1, $2, $3)",
                ctx.guild.id,
                r"Welcome {member.mention} to {server.name}!",
                True,
            )

        self.bot.loop.create_task(self.__ainit__())

        return await ctx.embed(
            title="Done!",
            description=f"Enabled the welcome message!{f' Use the `{codeblocksafe(ctx.clean_prefix)}welcome message` command to set a custom message!' if _ else ''}",
            colour=self.bot.config.colours.good,
        )

    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_roles=True)
    @_welcome.command(name="disable")
    async def _welcome_disable(self, ctx: NexusContext):
        """
        Disables the welcome message
        """
        if (
            ctx.guild.id in self._welcome_cache
            and self._welcome_cache[ctx.guild.id]["enabled"]
        ):
            await self.bot.db.execute(
                "UPDATE welcome SET enabled = $1 WHERE guild_id = $2",
                False,
                ctx.guild.id,
            )
            self.bot.loop.create_task(self.__ainit__())
            return await ctx.embed(
                title="Done!",
                description="Disabled the welcome message!",
                colour=self.bot.config.colours.good,
            )

        return await ctx.error("The welcome message is not enabled!")

    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_roles=True)
    @_welcome.command(name="channel")
    async def _welcome_channel(
        self, ctx: NexusContext, channel: Optional[TextChannel] = None
    ):
        """
        Set the channel for welcome messages
        """
        channel = channel or ctx.channel

        if (
            ctx.guild.id not in self._welcome_cache
            or not self._welcome_cache[ctx.guild.id]["enabled"]
        ):
            return await ctx.error("The welcome message is not enabled!")

        await self.bot.db.execute(
            "UPDATE welcome SET channel = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )

        self.bot.loop.create_task(self.__ainit__())
        return await ctx.embed(
            title="Done!",
            description=f"Set the welcome message channel to {channel.mention}",
            colour=self.bot.config.colours.good,
        )

    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_roles=True)
    @_welcome.command(name="message")
    async def _welcome_message(self, ctx: NexusContext, *, message: str):
        """
        Set the welcome message for your server

        Dynamic formatting options are possible. Note: all dynamic elements must be wrapped in curly braces {like this}

        member: The member that joined
            member.mention: The member mention
            member.id: The member id
            member.name: The member's name
            member.discriminator: The member's discriminator
            member.full_name: The member's name and discriminator

        server: The server they have joined
            server.name: The server's name
            server.id: The server's id
        """
        if (
            ctx.guild.id not in self._welcome_cache
            or not self._welcome_cache[ctx.guild.id]["enabled"]
        ):
            return await ctx.error("The welcome message is not enabled!")

        await self.bot.db.execute(
            "UPDATE welcome SET message = $1 WHERE guild_id = $2", message, ctx.guild.id
        )

        self.bot.loop.create_task(self.__ainit__())
        return await ctx.embed(
            title="Done!",
            description=f'Set the welcome message to "{message}"!',
            colour=self.bot.config.colours.good,
        )

    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_roles=True)
    @_welcome.command(name="role")
    async def _welcome_role(self, ctx: NexusContext, role: Role):
        """
        Set the welcome role

        This role is automatically given to someone when they join
        """
        if (
            ctx.guild.id not in self._welcome_cache
            or not self._welcome_cache[ctx.guild.id]["enabled"]
        ):
            return await ctx.error("The welcome message is not enabled!")

        await self.bot.db.execute(
            "UPDATE welcome SET role = $1 WHERE guild_id = $2", role.id, ctx.guild.id
        )

        self.bot.loop.create_task(self.__ainit__())
        return await ctx.embed(
            title="Done!",
            description=f"Set the welcome role to {role.mention}!",
            colour=self.bot.config.colours.good,
        )

    @Cog.listener(name="on_member_join")
    async def _send_member_join_messages(self, member: Member):
        with suppress(Exception):
            if (
                member.guild.id not in self._welcome_cache
                or not self._welcome_cache[member.guild.id]["enabled"]
                or not self._welcome_cache[member.guild.id]["channel"]
                or not self._welcome_cache[member.guild.id]["message"]
            ):
                return

            message = self.parser.parse(
                self._welcome_cache[member.guild.id]["message"],
                {"member": member, "server": member.guild},
            )

            await self._welcome_cache[member.guild.id]["channel"].send(message)

        with suppress(Exception):
            if role := self._welcome_cache[member.guild.id]["role"]:
                if role := member.guild.get_role(role):
                    await member.add_roles(role)

    @command(name="module")
    async def _module(
        self, ctx: NexusContext, module: Module, toggle: Optional[Toggle] = None
    ):
        if module is None:
            return await ctx.error(
                f"Please provide a valid module! Use {ctx.clean_prefix}modules to see all modules"
            )

        data = await self.bot.db.fetch(
            "SELECT blacklist FROM cogblacklist WHERE guild_id = $1", ctx.guild.id
        )
        cogs = [cog.qualified_name for cog in self.bot.cogs.values() if not cog.hidden]
        _l = data["blacklist"] if data else cogs

        await ctx.send(_l)

        if module == "all":
            if not toggle:
                return await ctx.embed(
                    title="All available modules",
                    description="\n".join(
                        f"{'❌' if cog in _l else '✅'} {cog}" for cog in cogs
                    ),
                )

            if data:
                await self.bot.db.execute(
                    "UPDATE cogblacklist SET blacklist = $1 WHERE guild_id = $2",
                    cogs if toggle else [],
                    ctx.guild.id,
                )
            else:
                await self.bot.db.execute(
                    "INSERT INTO cogblacklist VALUES ($1, $2)",
                    ctx.guild.id,
                    [] if toggle else cogs,
                )

            return await ctx.message.add_reaction("👍")

        cog: Cog = self.bot.get_cog(module)

        if cog is None or cog.hidden == True:
            return await ctx.error(
                f"Please provide a valid module! Use {ctx.clean_prefix}modules to see all modules"
            )

        if toggle is None:
            return await ctx.send_help(cog)

        if toggle and module in _l:
            return await ctx.error(f"{module} is already enabled!")

        if not toggle and module not in _l:
            return await ctx.error(f"{module} is already disabled!")

        if toggle:
            _l.append(module)
        else:
            _l.pop(_l.index(module))

        if data:
            await self.bot.db.execute(
                "UPDATE cogblacklist SET blacklist = $1 WHERE guild_id = $2",
                _l,
                ctx.guild.id,
            )
        else:
            await self.bot.db.execute(
                "INSERT INTO cogblacklist VALUES ($2, $1)", _l, ctx.guild.id
            )

        await ctx.message.add_reaction("👍")


def setup(bot: Nexus):
    bot.add_cog(Settings(bot))
