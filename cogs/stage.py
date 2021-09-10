import discord
from discord.ext import commands
from ds import ds
dis = ds()

class stage(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['sl'])
    @commands.has_permissions(administrator=True)
    async def stagelink(self, ctx, channel: discord.StageChannel, role: discord.Role): #: discord.StageChannel : discord.Role
        
        data = dis.jopen(f'stage\\stage{ctx.guild.id}')
        
        data[str(channel.id)] = str(role.id)
        
        dis.jdump(f'stage\\stage{ctx.guild.id}', data)

        await ctx.send(f'{channel.mention} is now linked to {role.name}')

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def stageunlink(self, ctx, channel: discord.StageChannel):
        data = dis.jopen(f'stage\\stage{ctx.guild.id}')

        data.pop(str(channel.id))

        dis.jdump(f'stage\\stage{ctx.guild.id}', data)

        await ctx.send(f'{channel.mention} is now unlinked.')



def setup(client):
    client.add_cog(stage(client))
