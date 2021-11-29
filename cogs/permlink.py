import discord
from discord.ext import commands
from discord.commands import Option
from bot import MyClient


class permlink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(
        description="Use to link all a channel and a role (after leaving channel, user will keep role)"
    )
    @commands.has_permissions(administrator=True)
    async def permlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.VoiceChannel, "Select a channel to link", required=True
        ),
        role: Option(discord.Role, "Select a role to link", required=True),
    ):

        data = self.client.redis.get_linked('permanent', ctx.guild.id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = []

        if str(role.id) not in data[str(channel.id)]:
            data[str(channel.id)].append(str(role.id))

            self.client.redis.update_linked('permanent', ctx.guild.id, data)

            await ctx.respond(
                f"Linked {channel.mention} with role: `@{role.name}`\nWhen a user leaves the channel, they will KEEP the role"
            )

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f"Please ensure my highest role is above `@{role.name}`")
        else:
            await ctx.respond(f"The channel and role are already linked.")

    @commands.slash_command(
        description='Use to unlink a "permanent" channel from a role'
    )
    @commands.has_permissions(administrator=True)
    async def permunlink(
        self,
        ctx: discord.ApplicationContext,
        channel: Option(
            discord.VoiceChannel, "Select a channel to link", required=True
        ),
        role: Option(discord.Role, "Select a role to link", required=True),
    ):

        data = self.client.redis.get_linked('permanent', ctx.guild.id)

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

                self.client.redis.update_linked('permanent', ctx.guild.id, data)

                await ctx.respond(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass


def setup(client):
    client.add_cog(permlink(client))
