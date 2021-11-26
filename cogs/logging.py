import discord
from discord.commands import Option
from discord.ext import commands
from bot import MyClient


class loggingC(commands.Cog):
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
            await ctx.respond("To enable, select a channel to send logs to.")
        elif enabled == True and channel:
            try:
                data = self.client.jopen("Data/guild_data", str(ctx.guild.id))

                data[str(ctx.guild.id)]["logging"] = str(channel.id)

                self.client.jdump("Data/guild_data", data)

                await ctx.respond(f"Successfully enabled logging in {channel.mention}")
            except:
                await ctx.respond(f"Unable to enable logging")
        elif enabled == False:
            try:
                data = self.client.jopen("Data/guild_data", str(ctx.guild.id))

                data[str(ctx.guild.id)]["logging"] = None

                self.client.jdump("Data/guild_data", data)

                await ctx.respond(f"Successfully disabled logging")
            except:
                await ctx.respond("Unable to disable logging")


def setup(client):
    client.add_cog(loggingC(client))
