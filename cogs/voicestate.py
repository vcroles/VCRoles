import discord
from discord.ext import commands
from bot import MyClient


class voicestate(commands.Cog):
    
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(guild_ids=[758392649979265024])
    async def test(self, ctx):
        await ctx.respond(f'{await self.client.all.join()}')

    @commands.slash_command(guild_ids=[758392649979265024])
    async def test2(self, ctx):
        await ctx.respond(f'{await self.client.stage.join()}')
        


def setup(client):
    client.add_cog(voicestate(client))