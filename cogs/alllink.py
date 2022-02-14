import discord
from discord.ext import commands
from discord.commands import Option
from bot import MyClient
from utils import Permissions


class AllLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description="Use to link all channels with a role")
    @Permissions.has_permissions(administrator=True)
    async def alllink(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Select a role to link", required=True),
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

    @commands.slash_command(description="Use to unlink all channels from a role")
    @Permissions.has_permissions(administrator=True)
    async def allunlink(
        self,
        ctx: discord.ApplicationContext,
        role: Option(discord.Role, "Select a role to link", required=True),
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

    @commands.slash_command(description="Use to create an exception to alllink")
    @Permissions.has_permissions(administrator=True)
    async def allexception(
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

    @commands.slash_command(description="Use to create an exception to alllink")
    @Permissions.has_permissions(administrator=True)
    async def allexceptionremove(
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


def setup(client: MyClient):
    client.add_cog(AllLink(client))
