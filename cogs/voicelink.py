import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from bot import MyClient
from utils import Permissions, handle_data_deletion


class VoiceLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    voice_commands = SlashCommandGroup("voice", "Rules to apply to voice channels")
    suffix_commands = voice_commands.create_subgroup(
        "suffix", "Suffix to add to the end of usernames"
    )
    reverse_commands = voice_commands.create_subgroup("reverse", "Reverse roles")

    @voice_commands.command(
        description="DEPRECATED Use to link a voice channel with a role"
    )
    @Permissions.has_permissions(administrator=True)
    async def link(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a voice channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("voice", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["roles"]:
            data[str(channel.id)]["roles"].append(str(role.id))

            self.client.redis.update_linked("voice", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @voice_commands.command(
        description="DEPRECATED Use to unlink a voice channel from a role"
    )
    @Permissions.has_permissions(administrator=True)
    async def unlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a voice channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("voice", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["roles"]:
            try:
                data[str(channel.id)]["roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("voice", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass

    @suffix_commands.command(
        description="DEPRECATED Use to set a suffix to add to the end of usernames"
    )
    @Permissions.has_permissions(administrator=True)
    async def add(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a voice channel to link"),
        suffix: Option(str, "Enter a suffix to add to the end of usernames"),
    ):
        data = self.client.redis.get_linked("voice", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked("voice", ctx.guild.id, data)

        await ctx.respond(f"Added suffix rule of `{suffix}` for {channel.mention}")

    @suffix_commands.command(
        description="DEPRECATED Use to remove a suffix to add to the end of usernames"
    )
    @Permissions.has_permissions(administrator=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a voice channel to link"),
    ):
        data = self.client.redis.get_linked("voice", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel has no associated rules.")
            return

        data[str(channel.id)]["suffix"] = ""

        data = handle_data_deletion(data, str(channel.id))

        self.client.redis.update_linked("voice", ctx.guild.id, data)

        await ctx.respond(f"Removed suffix rule for {channel.mention}")

    @reverse_commands.command(
        description="DEPRECATED Use to reverse roles in a voice channel", name="link"
    )
    @Permissions.has_permissions(administrator=True)
    async def reverse_link(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a voice channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("voice", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["reverse_roles"]:
            data[str(channel.id)]["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("voice", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @reverse_commands.command(
        description="DEPRECATED Use to unlink a voice channel from a role",
        name="unlink",
    )
    @Permissions.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.VoiceChannel, "Select a voice channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):

        data = self.client.redis.get_linked("voice", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["reverse_roles"]:
            try:
                data[str(channel.id)]["reverse_roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("voice", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass


def setup(client: MyClient):
    client.add_cog(VoiceLink(client))
