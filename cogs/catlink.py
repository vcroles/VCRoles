import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class CatLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    category_commands = SlashCommandGroup("category", "Rules to apply to categories")
    suffix_commands = category_commands.create_subgroup(
        "suffix", "Suffix to add to the end of usernames"
    )
    reverse_commands = category_commands.create_subgroup("reverse", "Reverse roles")

    @category_commands.command(
        description="Use to link all channels in a category with a role"
    )
    @Permissions.has_permissions(administrator=True)
    async def link(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.CategoryChannel, "Select a category to link", required=True
        ),
        role: Option(discord.Role, "Select a role to link", required=True),
    ):

        data = self.client.redis.get_linked("category", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["roles"]:
            data[str(channel.id)]["roles"].append(str(role.id))

            self.client.redis.update_linked("category", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @category_commands.command(description="Use to unlink a category from a role")
    @Permissions.has_permissions(administrator=True)
    async def unlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.CategoryChannel, "Select a category to link", required=True
        ),
        role: Option(discord.Role, "Select a role to link", required=True),
    ):

        data = self.client.redis.get_linked("category", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["roles"]:
            try:
                data[str(channel.id)]["roles"].remove(str(role.id))

                if (
                    not data[str(channel.id)]["roles"]
                    and not data[str(channel.id)]["suffix"]
                ):
                    data.pop(str(channel.id))

                self.client.redis.update_linked("category", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass

    @suffix_commands.command(
        description="Use to add a suffix to the end of usernames in a category"
    )
    @Permissions.has_permissions(administrator=True)
    async def add(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.CategoryChannel, "Select a category for the rule", required=True
        ),
        suffix: Option(str, "Add a suffix to the end of usernames", required=True),
    ):
        data = self.client.redis.get_linked("category", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked("category", ctx.guild.id, data)

        await ctx.respond(f"Added suffix rule of `{suffix}` for {channel.mention}")

    @suffix_commands.command(description="Use to remove a username suffix rule")
    @Permissions.has_permissions(administrator=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.CategoryChannel, "Select a category for the rule", required=True
        ),
    ):
        data = self.client.redis.get_linked("category", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel has no associated rules.")
            return

        data[str(channel.id)]["suffix"] = ""

        self.client.redis.update_linked("category", ctx.guild.id, data)

        await ctx.respond(f"Removed suffix rule for {channel.mention}")

    @reverse_commands.command(description="Use to add a reverse role link", name="link")
    @Permissions.has_permissions(administrator=True)
    async def rlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.CategoryChannel, "Select a category for the rule", required=True
        ),
        role: Option(discord.Role, "Select a role to link", required=True),
    ):
        data = self.client.redis.get_linked("category", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["reverse_roles"]:
            data[str(channel.id)]["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("category", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @reverse_commands.command(
        description="Use to unlink a category from a reverse role", name="unlink"
    )
    @Permissions.has_permissions(administrator=True)
    async def runlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.CategoryChannel, "Select a category to link", required=True
        ),
        role: Option(discord.Role, "Select a role to link", required=True),
    ):

        data = self.client.redis.get_linked("category", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["reverse_roles"]:
            try:
                data[str(channel.id)]["reverse_roles"].remove(str(role.id))

                if (
                    not data[str(channel.id)]["roles"]
                    and not data[str(channel.id)]["suffix"]
                ):
                    data.pop(str(channel.id))

                self.client.redis.update_linked("category", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass


def setup(client: MyClient):
    client.add_cog(CatLink(client))
