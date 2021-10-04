import discord
from discord.ext import commands
from discord.app import commands as app

class ping(commands.Cog):
    
    def __init__(self, client):
        self.client = client

    @app.slash_command(guild_ids=[758392649979265024])
    async def ping(self, ctx):
        await ctx.send(f'Pong! {round(self.client.latency*1000,1)} ms')

def setup(client):
    client.add_cog(ping(client))