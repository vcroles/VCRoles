import discord
from discord.ext import commands
import json
# import sys
# sys.path.insert(1, 'D:/Desktop/VC Roles/ds.py')
from ds import ds
import time
from time import localtime
dis = ds()

class dev(commands.Cog):

    def __init__(self, client):
        self.client = client

    # command
    @commands.command(aliases=['status'])
    @commands.check(dis.is_it_dev)
    async def changestatus(self, ctx, status = None, *, message = None):
        try:
            status = int(status)
        except:
            pass
        print(status, message)
        if status == 1:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description=f'Activity Type set to listening\nMessage set to {message}')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=message))
            await ctx.send(embed=status_embed)
        elif status == 2:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description=f'Activity Type set to Watching\nMessage set to {message}')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name=message))
            await ctx.send(embed=status_embed)
        elif status == 3:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description=f'Activity Type set to Playing\nMessage set to {message}')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.playing,name=message))
            await ctx.send(embed=status_embed)
        elif status == None:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Numbers For Status Changing**__',description='Listening - 1 \nWatching - 2\nPlaying - 3\n Plain Genric one - 4')
            await ctx.send(embed=status_embed)
        elif status == 4:
            status_embed = discord.Embed(colour=discord.Color.blue(),title='__**Success**__',description='Activity Type set to Listening\nMessage set to ?help - bit.ly/vcrole')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="?help - bit.ly/vcrole"))
            await ctx.send(embed=status_embed)

    @commands.command()
    @commands.check(dis.is_it_dev)
    async def count(self, ctx,command='all'):

        dis.counter('count')

        with open('counter.json','r') as f:
            count = json.load(f)

        if command == 'all':
            await ctx.send(count)
        elif command == 'CDE':
            await ctx.send(f'CDE is Smelly 💩\nP.S. Command has been used {count[command]} times')
        elif command == 'sam':
            await ctx.send(f'Sam is a poo head 💩\nP.S. Command has been used {count[command]} times')
        else:
            await ctx.send(f'The command {command} has been used {count[command]} times')

    @commands.command()
    @commands.check(dis.is_it_dev)
    async def send(self, ctx, channel_id: discord.TextChannel, *, message):
        await channel_id.send(message)

        dis.counter('send')

    @commands.command(aliases=['Servernum','Num','num'])
    @commands.check(dis.is_it_dev)
    async def servernum(self, ctx):
        await ctx.send(f'Bot is in {len(self.client.guilds)} servers')

        dis.counter('servernum')

    @commands.command(aliases=['shard'])
    @commands.check(dis.is_it_dev)
    async def shards(self, ctx):
        shards = self.client.shards
        for i in shards:
            await ctx.send(shards[i].id)
        latency = round(self.client.latency *1000)
        latencies = self.client.latencies
        shard_info = self.client.get_shard(0)
        shard_id = shard_info.id 
        shard_count = shard_info.shard_count
        shard_embed = discord.Embed(colour=discord.Colour.blue(), title='Sharding Info:', description=f'There are {shard_count} shards.\nThis is shard {shard_id} - latency: {latency} ms\nThe latency of other shards are: {latencies}')
        await ctx.send(embed=shard_embed)

    @commands.command()
    @commands.check(dis.is_it_dev)
    async def vcfix(self, ctx, server:str):
        # Adding a vcs .json
        try:
            data = dis.jopen(server)
        except:
            data = {}
            dis.jdump(server, data)
        # Adding server to prefixes file
        data = dis.jopen('prefixes')
        try:
            prefix = data[server]
        except:
            data[server] = '?'
            dis.jdump('prefixes', data)

        await ctx.send(f'Guild: {server} now has a vcs json, and the default prefix `?` has been assigned.')

    @commands.command()
    @commands.check(dis.is_it_dev)
    async def coglist(self, ctx):
        cog_list = ['dev','linkall','logging','privateroom','tts','utilites','vccontrol','vclink','voicestate']
        await ctx.send(f'The Cogs used in VC Roles are:\n{cog_list}')
        
    

def setup(client):
    client.add_cog(dev(client))