import discord
from discord.ext import commands
from ds import ds
dis = ds()

class linkall(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['Linkall', 'Vclinkall', 'vclinkall'])
    @commands.has_permissions(administrator=True)
    async def linkall(self, ctx, role: discord.Role):
        linked = dis.jopen(ctx.guild.id)

        linked['all'] = str(role.id)

        dis.jdump(ctx.guild.id, linked)

        num = len(ctx.guild.voice_channels)

        link_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Linked {num} voice channels with {role.mention}\nPlease make sure my highest role is above {role.mention} or I won\'t work'
        )
        await ctx.send(embed=link_embed)

        dis.counter('linkall')

    @commands.command(aliases=['Unlinkall', 'Vcunlinkall', 'vcunlinkall'])
    @commands.has_permissions(administrator=True)
    async def unlinkall(self, ctx):
        linked = dis.jopen(ctx.guild.id)

        role_id = linked['all']
        role = discord.utils.get(ctx.guild.roles, id=int(role_id))
        linked.pop('all')

        dis.jdump(ctx.guild.id, linked)

        num = len(ctx.guild.voice_channels)

        link_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Unlinked {num} voice channels from {role.mention}'
        )
        await ctx.send(embed=link_embed)

        dis.counter('unlinkall')

def setup(client):
    client.add_cog(linkall(client))