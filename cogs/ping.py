import discord
from discord.commands import slash_command
from discord.ext import commands

from bot import MyClient


class Ping(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @slash_command(description="Used to view the ping of the bot")
    async def ping(self, ctx):
        await ctx.respond(f"Pong! {round(self.client.latency*1000,1)} ms")


def setup(client: MyClient):
    client.add_cog(Ping(client))
