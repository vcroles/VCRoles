import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class AllLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    all_commands = SlashCommandGroup("all", "Rules to apply to all channels")
    exception_commands = all_commands.create_subgroup(
        "exception", "Channels to exclude from rules"
    )
    suffix_commands = all_commands.create_subgroup(
        "suffix", "Suffix to add to the end of usernames"
    )
    reverse_commands = all_commands.create_subgroup("reverse", "Reverse roles")

    @all_commands.command(description="Use to link all channels with a role")
    @Permissions.has_permissions(administrator=True)
    async def link(
        self,
        ctx: discord.ApplicationContext,
        role: Option(
            discord.Role,
            "Select a role to link",
        ),
    ):

        data = self.client.redis.get_linked("all", ctx.guild.id)

        if str(role.id) not in data["roles"]:
            data["roles"].append(str(role.id))

            self.client.redis.update_linked("all", ctx.guild.id, data)

            await ctx.respond(f"Linked all channels with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

        return self.client.incr_counter("all_link")

    @all_commands.command(description="Use to unlink all channels from a role")
    @Permissions.has_permissions(administrator=True)
    async def unlink(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("all", ctx.guild.id)

        if str(role.id) in data["roles"]:
            try:
                data["roles"].remove(str(role.id))

                self.client.redis.update_linked("all", ctx.guild.id, data)

                await ctx.respond(f"Unlinked all channels from role: `@{role.name}`")
            except:
                pass
        else:
            await ctx.respond(f"The channel and role are not linked.")

        return self.client.incr_counter("all_unlink")

    @exception_commands.command(description="Use to create an exception to alllink")
    @Permissions.has_permissions(administrator=True)
    async def add(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select an exception channel"),
    ):

        data = self.client.redis.get_linked("all", ctx.guild.id)

        try:
            if str(channel.id) not in data["except"]:
                data["except"].append(str(channel.id))

                self.client.redis.update_linked("all", ctx.guild.id, data)

                await ctx.respond(f"Added exception: `{channel.name}`")
            else:
                await ctx.respond(f"The channel is already an exception.")
        except:
            await ctx.respond(f"Unable to add exception")

        return self.client.incr_counter("all_add_exception")

    @exception_commands.command(description="Use to create an exception to alllink")
    @Permissions.has_permissions(administrator=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select an exception channel"),
    ):

        data = self.client.redis.get_linked("all", ctx.guild.id)

        if str(channel.id) in data["except"]:
            data["except"].remove(str(channel.id))

            self.client.redis.update_linked("all", ctx.guild.id, data)

            await ctx.respond(f"Removed {channel.mention} as an exception to alllink")
        else:
            await ctx.respond(f"Please select a valid exception channel")

        return self.client.incr_counter("all_remove_exception")

    @suffix_commands.command(description="Use to add a suffix to users")
    @Permissions.has_permissions(administrator=True)
    async def add(
        self,
        ctx: discord.ApplicationContext,
        suffix: Option(
            str,
            "The suffix to add to your username when joining any channel",
        ),
    ):
        data = self.client.redis.get_linked("all", ctx.guild.id)
        data["suffix"] = suffix
        self.client.redis.update_linked("all", ctx.guild.id, data)

        await ctx.respond(
            f"When members join any channel, their username will be appended with `{suffix}`"
        )

        return self.client.incr_counter("all_add_suffix")

    @suffix_commands.command(description="Use to remove a username suffix rule")
    @Permissions.has_permissions(administrator=True)
    async def remove(self, ctx: discord.ApplicationContext):
        data = self.client.redis.get_linked("all", ctx.guild.id)
        data["suffix"] = ""
        self.client.redis.update_linked("all", ctx.guild.id, data)

        await ctx.respond("Removed the username suffix rule")

        return self.client.incr_counter("all_remove_suffix")

    @reverse_commands.command(description="Use to add reverse links", name="link")
    @Permissions.has_permissions(administrator=True)
    async def reverse_link(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("all", ctx.guild.id)

        if str(role.id) not in data["reverse_roles"]:
            data["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("all", ctx.guild.id, data)

            await ctx.respond(f"Added reverse link: `@{role.name}`")
        else:
            await ctx.respond(f"The role is already a reverse link.")

        return self.client.incr_counter("all_reverse_link")

    @reverse_commands.command(description="Use to remove reverse links", name="unlink")
    @Permissions.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("all", ctx.guild.id)

        if str(role.id) in data["reverse_roles"]:
            try:
                data["reverse_roles"].remove(str(role.id))

                self.client.redis.update_linked("all", ctx.guild.id, data)

                await ctx.respond(f"Removed reverse link: `@{role.name}`")
            except:
                pass
        else:
            await ctx.respond(f"The role is not a reverse link.")

        return self.client.incr_counter("all_reverse_unlink")


def setup(client: MyClient):
    client.add_cog(AllLink(client))
