import discord
from discord.ext import commands
from discord.commands import Option
from bot import MyClient
from utils import Permissions


class CatLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(
        description="Use to link all channels in a category with a role"
    )
    @Permissions.has_permissions(administrator=True)
    async def catlink(
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
            data[str(channel.id)] = []

        if str(role.id) not in data[str(channel.id)]:
            data[str(channel.id)].append(str(role.id))

            self.client.redis.update_linked("category", ctx.guild.id, data)

            await ctx.respond(f"Linked {channel.mention} with role: `@{role.name}`")

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @commands.slash_command(description="Use to unlink a category from a role")
    @Permissions.has_permissions(administrator=True)
    async def catunlink(
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

        if str(role.id) in data[str(channel.id)]:
            try:
                data[str(channel.id)].remove(str(role.id))

                if not data[str(channel.id)]:
                    data.pop(str(channel.id))

                self.client.redis.update_linked("category", ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass


def setup(client: MyClient):
    client.add_cog(CatLink(client))
