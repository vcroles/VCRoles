import discord
from discord.ext import commands
from ds import ds
dis = ds()

class voicegen(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=["voicegen","generator","Generator"]) 
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(administrator=True)
    async def generatorsetup(self, ctx, *, vcname= "Voice Generator"):
        # Make entry in generator.json for guild
        generator = dis.jopen("generator")

        try:
            guild_data = generator[str(ctx.guild.id)]
        except:
            generator[str(ctx.guild.id)] = {}
            guild_data = generator[str(ctx.guild.id)]

        #Make Generator Category

        category = await ctx.guild.create_category(name="Voice Generators")

        # Make Generator VC
        
        channel = await ctx.guild.create_voice_channel(name=vcname, category=category)

        guild_data['category'] = category.id
        guild_data['lobby_name'] = vcname
        guild_data['lobby_id'] = channel.id
        guild_data['open_rooms'] = {}

        generator[str(ctx.guild.id)] = guild_data

        dis.jdump("generator", generator)

        creation_embed = discord.Embed(color=discord.Color.green(),title='**Voice Generator Setup**', description=f'The category **{category.name}** and voice channel **{channel.name}** have been created.\n Join the voice channel to generate a voice channel.')
        await ctx.send(embed=creation_embed)

        dis.counter('voicegen')

    @commands.command(aliases=["generatorremove"])
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(administrator=True)
    async def Generatorremove(self, ctx):
        generator = dis.jopen("generator")

        guild_data = generator[str(ctx.guild.id)]
        channel = guild_data['lobby_id']
        category = guild_data['category']

        channel = ctx.guild.get_channel(channel)
        category = discord.utils.get(ctx.guild.categories, id=category)
        await channel.delete()
        await category.delete()

        generator.pop(str(ctx.guild.id))

        dis.jdump("generator", generator)
        
        removal_embed = discord.Embed(color=discord.Color.green(),title='**Voice Generator Removed**', description=f'The Voice Generator has been removed to set it back up use the command `{dis.get_prefix(ctx.message)}generator`')
        await ctx.send(embed=removal_embed)

        dis.counter('voicegenrem')



def setup(client):
    client.add_cog(voicegen(client))