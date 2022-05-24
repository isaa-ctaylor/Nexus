from contextlib import suppress
import random
from typing import Optional

from discord.embeds import Embed
from discord.enums import ButtonStyle
from discord.ext.commands.converter import Converter, MemberConverter
from discord.ext.commands.core import check, has_guild_permissions
from discord.ext.commands.errors import BadArgument, CommandError
from discord.interactions import Interaction
from discord.member import Member
from discord.message import Message
from discord.role import Role
from discord.ui import Button, View, button
from utils.subclasses.bot import Nexus
from utils.subclasses.cog import Cog
from utils.subclasses.command import command
from utils.subclasses.context import NexusContext


def has_required_role():
    async def predicate(ctx: NexusContext):
        data = await ctx.bot.db.fetch(
            "SELECT * FROM config WHERE guild_id = $1", ctx.guild.id
        )
        if not data or not data["role"]:
            return True
        if data["role"] in [r.id for r in ctx.author.roles]:
            return True
        if ctx.author.guild_permissions.manage_messages:
            return True
        raise CommandError(
            f"You do not have the required {ctx.guild.get_role(data['role'])} role!"
        )

    return check(predicate)


class BulkQuotes(Converter):
    async def convert(self, ctx: NexusContext, argument: str):
        result = {}
        quotes = argument.splitlines()
        for quote in quotes:
            parts = quote.split("~")
            if len(parts) != 2:
                continue
            if (o := parts[1].strip().lower()) not in result:
                result[o] = []
            result[parts[1].strip().lower()].append(parts[0].strip())
        return result


class Quotes(Cog):
    """
    Commands for storing quotes
    """

    def __init__(self, bot: Nexus):
        self.bot = bot

    async def _do_quote_info(self, ctx: NexusContext, index: int):
        quote = await self.bot.db.fetch("SELECT * FROM quotes WHERE id = $1", index)

        owner = self.bot.get_user(quote["owner_id"]) or await self.bot.fetch_user(
            quote["owner_id"]
        )

        embed = (
            Embed(
                title=f"{owner}'s quote",
                description=quote["quote"],
                colour=self.bot.config.colours.neutral,
            )
            .add_field(name="Owner", value=owner.mention)
            .add_field(name="Likes", value=len(set(quote["likes"])))
            .add_field(name="Created", value=f"<t:{quote['created']}:D>")
        )

        class LikeItView(View):
            @button(label="Like", style=ButtonStyle.green, emoji="👍")
            async def like(this, button: Button, interaction: Interaction):
                data = await self.bot.db.fetch(
                    "SELECT * FROM quotes WHERE id = $1", index
                )
                likes: set = set(data["likes"])
                if interaction.user.id == data["owner_id"]:
                    return await interaction.response.send_message(
                        embed=Embed(
                            title="Error!",
                            description="```\nYou cannot like your own quote!```",
                            colour=self.bot.config.colours.bad,
                        ),
                        ephemeral=True,
                    )
                if interaction.user.id in likes:
                    likes.remove(interaction.user.id)
                    await interaction.response.send_message(
                        embed=Embed(
                            description=f"You unliked {owner.mention}'s quote!",
                            colour=self.bot.config.colours.bad,
                        ),
                        ephemeral=True,
                    )

                else:
                    likes.add(interaction.user.id)
                    await interaction.response.send_message(
                        embed=Embed(
                            description=f"You liked {owner.mention}'s quote!",
                            colour=self.bot.config.colours.good,
                        ),
                        ephemeral=True,
                    )
                await self.bot.db.execute(
                    "UPDATE quotes SET likes = $1 WHERE id = $2", likes, index
                )
                likes = await self.bot.db.fetch(
                    "SELECT likes FROM quotes WHERE id = $1", index
                )
                embed.remove_field(1)
                embed.insert_field_at(1, name="Likes", value=len(set(likes["likes"])))
                await interaction.message.edit(embed=embed)

        await ctx.send(
            embed=embed,
            view=LikeItView(timeout=None),
        )

    def _do_mass_quotes(self, quotes: list):
        quotes = {
            person: [q for q in quotes if q["owner_id"] == person]
            for person in {q["owner_id"] for q in quotes}
        }

        x = 0
        pages = [""]
        for k, v in quotes.items():
            if len(f"{pages[x]}\n\n<@{k}>") >= 4096:
                pages.append(f"<@{k}>")
                x += 1
            else:
                pages[x] += f"\n\n<@{k}>"

            for quote in v:
                if len(f"{pages[x]}\n**{quote['id']}:** {quote['quote']}") > 4096:
                    pages.append(f"**{quote['id']}:** {quote['quote']}")
                    x += 1
                else:
                    pages[x] += f"\n**{quote['id']}:** {quote['quote']}"

        return pages

    @command(name="view", usage="<id> [number]", invoke_without_command=True)
    async def _quote(self, ctx: NexusContext, *, index: str):
        """
        See a quote's information, given the id

        If id is "random", then number can be specified, and a maximum of that many quotes will be returned
        """
        with suppress(Exception):
            index = int(index.strip())

        if ctx.invoked_subcommand:
            return

        num = 1

        if isinstance(index, str):
            if len(index.split(" ")) == 2:
                if index.split(" ")[0].isnumeric():
                    index = int(float(index.split(" ")[0]))

                elif index.split(" ")[0].strip().lower() == "random":
                    if index.split(" ")[1].isnumeric():
                        num = int(float(index.split(" ")[1]))
                    index = "random"

            elif index.lower() != "random":
                return await ctx.error("Provide a valid id!")

        quotes = await self.bot.db.fetch(
            "SELECT * FROM quotes WHERE guild_id = $1", ctx.guild.id, one=False
        )
        if index == "random":
            quotes = random.sample(quotes, min(num, len(quotes)))
            pages = self._do_mass_quotes(quotes)
            return await ctx.paginate(
                [
                    Embed(description=page, colour=self.bot.config.colours.neutral)
                    for page in pages
                ]
            )

        if index not in [q["id"] for q in quotes]:
            return await ctx.error(f"No quote with id {index} found!")

        await self._do_quote_info(ctx, index)

    @has_required_role()
    @command(name="quote-add", aliases=["quoteadd"], usage="<member> <quote>")
    async def _add(
        self,
        ctx: NexusContext,
        member: Optional[Member] = None,
        *,
        quote: Optional[str] = None,
    ):
        """
        Add a quote to the database

        Quotes can be added by typing them out (e.g. quoteadd @Someone#1234 Cheese) or by replying to a message
        """
        created = int(ctx.message.created_at.timestamp())
        if not member and not quote:
            if (
                not ctx.message.reference
                or not (
                    ctx.message.reference.resolved
                    or await ctx.channel.fetch_message(ctx.message.reference.message_id)
                ).content
            ):
                return await ctx.error("Missing quote!")

            message = ctx.message.reference.resolved or await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )

            member = message.author
            quote = message.content
            created = int(message.created_at.timestamp())

        elif member and not quote:
            if (
                not ctx.message.reference
                or not (
                    ctx.message.reference.resolved
                    or await ctx.channel.fetch_message(ctx.message.reference.message_id)
                ).content
            ):
                return await ctx.error("Missing quote!")

            message = ctx.message.reference.resolved or await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )

            quote = message.content

        elif not member:
            member = ctx.author

        await self.bot.db.execute(
            "INSERT INTO quotes (guild_id, owner_id, likes, created, quote) VALUES ($1, $2, $3, $4, $5)",
            ctx.guild.id,
            member.id,
            [],
            created,
            quote,
        )

        return await ctx.embed(
            title="Quote added",
            description=f'Added the quote "{quote}" - {member.mention} to the database!',
            colour=self.bot.config.colours.good,
        )

    @has_required_role()
    @command(name="quote-remove", aliases=["quoteremove"], usage="<id>")
    async def _remove(self, ctx: NexusContext, index: int):
        """
        Remove a quote from the database

        You may only remove your own quote, unless you have the Manage Messages permission
        """
        quotes = await self.bot.db.fetch(
            "SELECT id FROM quotes WHERE guild_id = $1", ctx.guild.id, one=False
        )

        if index not in [q["id"] for q in quotes]:
            return await ctx.error(f"No quote with id {index} found!")

        quote = await self.bot.db.fetch(
            "SELECT * FROM quotes WHERE guild_id = $1 and id = $2", ctx.guild.id, index
        )
        if (
            quote["owner_id"] != ctx.author.id
            and not ctx.author.guild_permissions.manage_messages
        ):
            return await ctx.error("You cannot remove other people's quotes!")

        await self.bot.db.execute(
            "DELETE FROM quotes WHERE guild_id = $1 and id = $2", ctx.guild.id, index
        )

        await ctx.message.add_reaction("👍")

    @command(name="list")
    async def _list(self, ctx: NexusContext, member: Optional[Member] = None):
        """
        See all quotes by a specified member, or all quotes for your server if no member specified

        Quotes are displayed in the format "quote (ID: id)"
        """
        if member:
            quotes = await self.bot.db.fetch(
                "SELECT * FROM quotes WHERE owner_id = $1 and guild_id = $2",
                member.id,
                ctx.guild.id,
                one=False,
            )

            if not quotes:
                return await ctx.error(f"{member} has no quotes!")

            x = 0
            pages = [""]
            for quote in quotes:
                if len(pages[x] + f"\n**{quote['id']}:** {quote['quote']}") > 4096:
                    pages.append(f"**{quote['id']}:** {quote['quote']}")
                    x += 1
                else:
                    pages[x] += f"\n**{quote['id']}:** {quote['quote']}"
        else:
            quotes = await self.bot.db.fetch(
                "SELECT * FROM quotes WHERE guild_id = $1", ctx.guild.id, one=False
            )

            if not quotes:
                return await ctx.error("No quotes yet!")

            pages = self._do_mass_quotes(quotes)

        await ctx.paginate(
            [
                Embed(description=page, colour=self.bot.config.colours.neutral)
                for page in pages
            ]
        )

    @has_guild_permissions(manage_messages=True)
    @command(name="role")
    async def _role(self, ctx: NexusContext, role: Optional[Role] = None):
        """
        Lock quote commands to a specific role

        To disable the lock, do not specify a role when running the command
        """
        data = await self.bot.db.fetch(
            "SELECT * FROM config WHERE guild_id = $1", ctx.guild.id
        )
        if not data:
            await self.bot.db.execute(
                "INSERT INTO config VALUES ($1, $2)", ctx.guild.id, None
            )
        await self.bot.db.execute(
            "UPDATE config SET role = $1 WHERE guild_id = $2",
            role.id if role is not None else role,
            ctx.guild.id,
        )

        await ctx.paginate(
            Embed(
                title="Done!",
                description="Removed the role lock, now everyone can use quote commands!"
                if not role
                else f"Set the role lock to {role.mention}. Now only users with the {role.mention} role can use quote commands!",
                colour=self.bot.config.colours.good,
            )
        )

    @command(name="profile")
    async def _profile(self, ctx: NexusContext, member: Optional[Member] = None):
        """
        See stats on a person
        """
        member = member or ctx.author

        q = await self.bot.db.fetch(
            "SELECT * FROM quotes WHERE guild_id = $1 and owner_id = $2",
            ctx.guild.id,
            member.id,
            one=False,
        )

        quotes = reversed(
            sorted(
                q,
                key=lambda x: len(x["likes"]),
            )
        )

        if not quotes:
            _ = "No quotes yet!"
        else:
            _ = "\n".join(
                f"{i+1}) {q['quote']}" for i, q in enumerate(list(quotes)[:5])
            )

        embed = (
            Embed(title=f"{member}'s profile", colour=self.bot.config.colours.neutral)
            .add_field(name="Top quotes", value=f"```\n{_}```")
            .add_field(
                name="Total number of quotes",
                value=f"```py\n{len(q)}```",
                inline=False,
            )
        )
        await ctx.paginate(embed)

    @has_guild_permissions(manage_messages=True)
    @command(name="import")
    async def _import(self, ctx: NexusContext, *, bulk: BulkQuotes):
        """
        A temporary command to import quotes in bulk

        This command will parse a message containing a bulk of quotes, then prompt you to identify each person it finds. This can be done by mentioning or sending the person's id/name
        """
        assigned = {}
        message: Optional[Message] = None
        for owner in bulk:
            embed = Embed(
                title="Who is it?",
                description=f"Please identify {owner}!",
                colour=self.bot.config.colours.neutral,
            )
            if message is not None:
                await message.edit(embed=embed)
            else:
                message = await ctx.send(embed=embed)

            m = await self.bot.wait_for(
                "message",
                check=lambda m: m.channel.id == ctx.channel.id
                and m.author.id == ctx.author.id,
            )
            try:
                member = await MemberConverter().convert(ctx, m.content)
            except (BadArgument, CommandError):
                return await message.edit("Invalid member passed, aborting!")
            if assigned.get(member, None) is None:
                assigned[member] = []
            assigned[member] += bulk[owner]

        for member, quotes in assigned.items():
            await self.bot.db.executemany(
                "INSERT INTO quotes (guild_id, owner_id, likes, created, quote) VALUES ($1, $2, $3, $4, $5)",
                [
                    [
                        ctx.guild.id,
                        member.id,
                        [],
                        int(ctx.message.created_at.timestamp()),
                        quote,
                    ]
                    for quote in quotes
                ],
            )

        allquotes = []
        for q in assigned.values():
            allquotes += q

        return await ctx.embed(
            title="Done!",
            description=f"Inserted {len(allquotes)} quotes!",
            colour=self.bot.config.colours.good,
        )


async def setup(bot: Nexus):
    await bot.add_cog(Quotes(bot))
