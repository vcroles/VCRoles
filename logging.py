import discord
from discord.ext import commands
from ds import ds
dis = ds()

class logging(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=[])
    @commands.has_permissions(administrator=True)
    async def logging(self, ctx, action, channel:discord.TextChannel):
        logging_channels = dis.jopen("logging")
        fine = True

        if action == 'set' and fine == True:
            logging_channels[str(ctx.guild.id)] = str(channel.id)

            dis.jdump("logging", logging_channels)

            logging_embed = discord.Embed(colour=discord.Colour.teal(), description=f'Audit Logging channel set for {channel.mention}')
            await ctx.send(embed=logging_embed)
        
        elif action == 'remove' and fine == True:
            logging_channels.pop(str(ctx.guild.id))

            dis.jdump("logging", logging_channels)

            logging_embed = discord.Embed(colour=discord.Colour.teal(), description=f'Audit Logging channel removed')
            await ctx.send(embed=logging_embed)

        else:
            logging_embed = discord.Embed(colour=discord.Colour.teal(), description=f'Please use either: `{dis.get_prefix(ctx.message)}logging set #channel` or `{dis.get_prefix(ctx.message)}logging remove`')
            await ctx.send(embed=logging_embed)

        dis.counter('logging')

def setup(client):
    client.add_cog(logging(client))