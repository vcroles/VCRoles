import discord
from discord.commands import Option
from discord.ext import commands
from bot import MyClient


class Logging(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description="Used to enable disable logging, in a channel.")
    @commands.has_permissions(administrator=True)
    async def logging(
        self,
        ctx: discord.ApplicationContext,
        enabled: Option(bool, "Enabled?", required=True),
        channel: Option(discord.TextChannel, "Logging channel:", required=False),
    ):
        if enabled == True and not channel:
            channel = ctx.channel
        if enabled == True and channel:
            try:
                data = self.client.redis.get_guild_data(ctx.guild.id)

                data["logging"] = str(channel.id)

                self.client.redis.update_guild_data(ctx.guild.id, data)

                await ctx.respond(f"Successfully enabled logging in {channel.mention}")
            except:
                await ctx.respond(f"Unable to enable logging")
        elif enabled == False:
            try:
                data = self.client.redis.get_guild_data(ctx.guild.id)

                data["logging"] = None

                self.client.redis.update_guild_data(ctx.guild.id, data)

                await ctx.respond(f"Successfully disabled logging")
            except:
                await ctx.respond("Unable to disable logging")


def setup(client: MyClient):
    client.add_cog(Logging(client))
