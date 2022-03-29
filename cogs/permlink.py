import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from bot import MyClient
from utils import Permissions, handle_data_deletion


class PermLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    perm_commands = SlashCommandGroup(
        "permanent", "Rules to apply to permanent channels"
    )
    suffix_commands = perm_commands.create_subgroup(
        "suffix", "Suffix to add to the end of usernames"
    )
    reverse_commands = perm_commands.create_subgroup("reverse", "Reverse roles")

    @perm_commands.command(
        description="Use to link all a channel and a role (after leaving channel, user will keep role)"
    )
    @Permissions.has_permissions(administrator=True)
    async def link(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("permanent", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["roles"]:
            data[str(channel.id)]["roles"].append(str(role.id))

            self.client.redis.update_linked("permanent", ctx.guild.id, data)

            await ctx.respond(
                f"Linked {channel.mention} with role: `@{role.name}`\nWhen a user leaves the channel, they will KEEP the role"
            )

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

        return self.client.incr_counter("perm_link")

    @perm_commands.command(
        description='Use to unlink a "permanent" channel from a role'
    )
    @Permissions.has_permissions(administrator=True)
    async def unlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("permanent", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["roles"]:
            try:
                data[str(channel.id)]["roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("permanent", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass

        return self.client.incr_counter("perm_unlink")

    @suffix_commands.command(
        description="Use to set a suffix to add to the end of usernames"
    )
    @Permissions.has_permissions(administrator=True)
    async def add(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a channel to link"),
        suffix: Option(str, "Enter a suffix to add to the end of usernames"),
    ):
        data = self.client.redis.get_linked("permanent", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked("permanent", ctx.guild.id, data)

        await ctx.respond(f"Added suffix rule of `{suffix}` for {channel.mention}")

        return self.client.incr_counter("perm_suffix_add")

    @suffix_commands.command(description="Use to remove a suffix rule from a channel")
    @Permissions.has_permissions(administrator=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a channel to link"),
    ):
        data = self.client.redis.get_linked("permanent", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel has no associated rules.")
            return

        data[str(channel.id)]["suffix"] = ""

        data = handle_data_deletion(data, str(channel.id))

        self.client.redis.update_linked("permanent", ctx.guild.id, data)

        await ctx.respond(f"Removed suffix rule for {channel.mention}")

        return self.client.incr_counter("perm_suffix_remove")

    @reverse_commands.command(
        description="Use to reverse roles",
        name="link",
    )
    @Permissions.has_permissions(administrator=True)
    async def reverse_link(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("permanent", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["reverse_roles"]:
            data[str(channel.id)]["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("permanent", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

        return self.client.incr_counter("perm_reverse_link")

    @reverse_commands.command(
        description="Use to unlink a reverse role",
        name="unlink",
    )
    @Permissions.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("permanent", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            return await ctx.respond(f"The channel and role are not linked.")

        if str(role.id) in data[str(channel.id)]["reverse_roles"]:
            try:
                data[str(channel.id)]["reverse_roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("permanent", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass

        return self.client.incr_counter("perm_reverse_unlink")


def setup(client: MyClient):
    client.add_cog(PermLink(client))
