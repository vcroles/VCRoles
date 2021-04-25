import discord
from discord.ext import commands
from ds import ds
dis = ds()

class privateroom(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=["Private","private","privatesetup"]) 
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(administrator=True)
    async def PrivateSetup(self, ctx, *, vcname= "Create Private Room"):
        # Make entry in private.json for guild
        private = dis.jopen("private")

        try:
            guild_data = private[str(ctx.guild.id)]
        except:
            private[str(ctx.guild.id)] = {}
            guild_data = private[str(ctx.guild.id)]

        #Make Private VC Category

        category = await ctx.guild.create_category(name="Private Rooms")

        # Make Lobby VC
        
        channel = await ctx.guild.create_voice_channel(name=vcname, category=category)

        guild_data['category'] = category.id
        guild_data['lobby_name'] = vcname
        guild_data['lobby_id'] = channel.id
        guild_data['open_rooms'] = {}
        guild_data['waiting_rooms'] = {}

        private[str(ctx.guild.id)] = guild_data

        dis.jdump("private", private)

        creation_embed = discord.Embed(color=discord.Color.green(),title='**Private Rooms Setup**', description=f'The category **{category.name}** and voice channel **{channel.name}** have been created.\n To create a Private room join the voice channel.')
        await ctx.send(embed=creation_embed)

        dis.counter('privatesetup')

    @commands.command(aliases=["privateremove"])
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(administrator=True)
    async def Privateremove(self, ctx):
        private = dis.jopen("private")

        guild_data = private[str(ctx.guild.id)]
        channel = guild_data['lobby_id']
        category = guild_data['category']

        channel = ctx.guild.get_channel(channel)
        category = discord.utils.get(ctx.guild.categories, id=category)
        await channel.delete()
        await category.delete()

        private.pop(str(ctx.guild.id))

        dis.jdump("private", private)
        
        removal_embed = discord.Embed(color=discord.Color.green(),title='**Private Rooms Removed**', description=f'Private rooms have been removed to set them back up use the command `{dis.get_prefix(ctx.message)}private`')
        await ctx.send(embed=removal_embed)

        dis.counter('privateremove')



def setup(client):
    client.add_cog(privateroom(client))