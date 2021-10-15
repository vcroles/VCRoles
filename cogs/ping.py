import discord
from discord.ext import commands

class ping(commands.Cog):
    
    def __init__(self, client):
        self.client = client

    @commands.slash_command(guild_ids=[758392649979265024])
    async def ping(self, ctx):
        await ctx.respond(f'Pong! {round(self.client.latency*1000,1)} ms')

def setup(client):
    client.add_cog(ping(client))