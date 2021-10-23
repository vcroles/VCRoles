import discord, json
from discord.commands import Option
from discord import ApplicationContext
from discord.ext import commands
from bot import MyClient

with open('Data/config.json', 'r') as f:
    config = json.load(f)

class dev(commands.Cog):

    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(guild_ids=config['MANAGE_GUILD_IDS'], description='DEVELOPER COMMAND')
    @commands.is_owner()
    async def change_status(self, ctx: ApplicationContext, status = None, message = Option(str, 'Message')):
        try:
            status = int(status)
        except:
            pass
        print(status, message)
        if status == 1:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description=f'Activity Type set to listening\nMessage set to {message}')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=message))
            await ctx.respond(embed=status_embed)
        elif status == 2:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description=f'Activity Type set to Watching\nMessage set to {message}')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=message))
            await ctx.respond(embed=status_embed)
        elif status == 3:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description=f'Activity Type set to Playing\nMessage set to {message}')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing,name=message))
            await ctx.respond(embed=status_embed)
        elif status == None:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Numbers For Status Changing**__',description='Listening - 1 \nWatching - 2\nPlaying - 3\n Plain Genric one - 4')
            await ctx.respond(embed=status_embed)
        elif status == 4:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description='Activity Type set to Listening\nMessage set to ?help - bit.ly/vcrole')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="?help - bit.ly/vcrole"))
            await ctx.respond(embed=status_embed)
    
    @commands.slash_command(guild_ids=config['MANAGE_GUILD_IDS'], description='DEVELOPER COMMAND')
    @commands.is_owner()
    async def servernum(self, ctx):
        await ctx.respond(f'Bot is in {len(self.client.guilds)} servers')

    @commands.slash_command(guild_ids=config['MANAGE_GUILD_IDS'], description='DEVELOPER COMMAND')
    @commands.is_owner()
    async def shards(self, ctx):
        shards = self.client.shards
        latency = round(self.client.latency *1000)
        latencies = self.client.latencies
        shard_info = self.client.get_shard(0)
        shard_id = shard_info.id 
        shard_count = shard_info.shard_count
        shard_embed = discord.Embed(colour=discord.Colour.blue(), title='Sharding Info:', description=f'There are {shard_count} shards.\nThis is shard {shard_id} - latency: {latency} ms\nThe latency of other shards are: {latencies}')
        await ctx.respond(embed=shard_embed)

    @commands.slash_command(guild_ids=config['MANAGE_GUILD_IDS'], description='DEVELOPER COMMAND')
    @commands.is_owner()
    async def coglist(self, ctx):
        await ctx.respond(f'The cogs are:\n{self.client.cogs}')

def setup(client):
    client.add_cog(dev(client))