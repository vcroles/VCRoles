import discord
from discord.commands import Option, SlashCommandGroup
from discord.ext import commands

from bot import MyClient
from utils import Permissions, handle_data_deletion


class StageLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    stage_commands = SlashCommandGroup("stage", "Rules to apply to stage channels")
    suffix_commands = stage_commands.create_subgroup(
        "suffix", "Suffix to add to the end of usernames"
    )
    reverse_commands = stage_commands.create_subgroup("reverse", "Reverse roles")

    @stage_commands.command(
        description="DEPRECATED Use to link a stage channel with a role"
    )
    @Permissions.has_permissions(administrator=True)
    async def link(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.StageChannel, "Select a stage channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):
        data = self.client.redis.get_linked("stage", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["roles"]:
            data[str(channel.id)]["roles"].append(str(role.id))

            self.client.redis.update_linked("stage", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @stage_commands.command(
        description="DEPRECATED Use to unlink a stage channel from a role"
    )
    @Permissions.has_permissions(administrator=True)
    async def unlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.StageChannel, "Select a stage channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):
        data = self.client.redis.get_linked("stage", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["roles"]:
            try:
                data[str(channel.id)]["roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("stage", ctx.guild.id, data)

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
        channel: Option(discord.StageChannel, "Select a stage channel to link"),
        suffix: Option(str, "Enter a suffix to add to the end of usernames"),
    ):
        data = self.client.redis.get_linked("stage", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked("stage", ctx.guild.id, data)

        await ctx.respond(
            f"Added suffix `{suffix}` to the end of usernames in {channel.mention}"
        )

    @suffix_commands.command(
        description="DEPRECATED Use to remove a suffix from the end of usernames"
    )
    @Permissions.has_permissions(administrator=True)
    async def remove(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.StageChannel, "Select a stage channel to link"),
    ):
        data = self.client.redis.get_linked("stage", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel has no associated rules.")
            return

        data[str(channel.id)]["suffix"] = ""

        data = handle_data_deletion(data, str(channel.id))

        self.client.redis.update_linked("stage", ctx.guild.id, data)

        await ctx.respond(f"Removed suffix rule for {channel.mention}")

    @reverse_commands.command(
        description="DEPRECATED Use to reverse roles in a stage channel", name="link"
    )
    @Permissions.has_permissions(administrator=True)
    async def rlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.StageChannel, "Select a stage channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):
        data = self.client.redis.get_linked("stage", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["reverse_roles"]:
            data[str(channel.id)]["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("stage", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @reverse_commands.command(
        description="DEPRECATED Use to unlink a stage channel from a role",
        name="unlink",
    )
    @Permissions.has_permissions(administrator=True)
    async def runlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(discord.StageChannel, "Select a stage channel to link"),
        role: Option(discord.Role, "Select a role to link"),
    ):
        data = self.client.redis.get_linked("stage", ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            await ctx.respond(f"The channel and role are not linked.")
            return

        if str(role.id) in data[str(channel.id)]["reverse_roles"]:
            try:
                data[str(channel.id)]["reverse_roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("stage", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass


def setup(client: MyClient):
    client.add_cog(StageLink(client))
