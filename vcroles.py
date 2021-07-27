## VC Roles Bot
## Version 1.5


# Importing Libraries

import discord
from discord.ext import commands, tasks
import os
from ds import ds
import time
from time import localtime
startTime = time.time()
import psutil
from psutil import virtual_memory
# import discordbotdash.dash as dbd


def get_prefix(client, message):
    prefixes = dis.jopen('prefixes')
    
    return prefixes[str(message.guild.id)]

def uptime(cur_time):
    Time_Sec = int(cur_time - startTime)
    while Time_Sec > 60:
        Time_Sec -= 60
    Time_Min = int((cur_time - startTime) / 60)
    while Time_Min > 60:
        Time_Min -= 60
    Time_Hour = int((cur_time - startTime) / 60 ** 2)
    total_uptime = f'{Time_Hour}:{Time_Min}:{Time_Sec}'
    return total_uptime


# Bot Initiation


dis = ds()
intents = discord.Intents(messages = True, guilds = True, reactions = True, voice_states = True)
# client = commands.Bot(command_prefix = get_prefix, intents = intents)
client = commands.AutoShardedBot(command_prefix = get_prefix, intents = intents)
client.remove_command('help')
bot_token = 'Nzc1MDI1Nzk3MDM0NTQxMTA3.X6gVBQ.ikWFDCxKHkhESR6UcYtbBs8lHOE'
#Bot - Nzc1MDI1Nzk3MDM0NTQxMTA3.X6gVBQ.ikWFDCxKHkhESR6UcYtbBs8lHOE
#Testing - NzY0OTA1NzI2ODMyOTM0OTMz.X4ND-A.5QxAuNQ9qCe5i7VgqylOGWspIcg
#Events


@client.event 
async def on_guild_join(guild):
    prefixes = dis.jopen('prefixes')
    
    prefixes[str(guild.id)] = '?'

    dis.jdump('prefixes', prefixes)
    
    dis.jdump(guild.id, {})

    dis.jdump(f'category\\cat{guild.id}', {})

    print(f'VC lists for {guild.id} created. Server name: {guild.name}')
    discord_terminal = client.get_channel(776117712074047539)
    await discord_terminal.send(f'Joined server: {guild.name}\nVC list created, name: {guild.id}')
    dev_terminal = client.get_channel(869354307328307230)
    await dev_terminal.send(f'Joined server: {guild.name}\nVC list created, name: {guild.id}')

    server_count = client.get_channel(869587186318716959)
    await server_count.edit(name=f'{len(client.guilds)} - Servers')

@client.event
async def on_guild_remove(guild):
    prefixes = dis.jopen('prefixes')
    
    prefixes.pop(str(guild.id))

    dis.jdump('prefixes', prefixes)

    dis.jdump(guild.id, {})
    
    print(f'VC list for {guild.id} reset. Server name: {guild.name}')
    print(f'Bot left server {guild.name}, {guild.id}')
    discord_terminal = client.get_channel(776117712074047539)
    await discord_terminal.send(f'Bot left server {guild.name}, {guild.id}\nVC list reset')
    dev_terminal = client.get_channel(869354307328307230)
    await dev_terminal.send(f'Bot left server {guild.name}, {guild.id}\nVC list reset')

    server_count = client.get_channel(869587186318716959)
    await server_count.edit(name=f'{len(client.guilds)} - Servers')

@client.event
async def on_ready():
    await client.change_presence(status=discord.Status.online)
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name='Voice Channels - ?help'))
    # await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="?help - bit.ly/vcrole"))
    
    serverss = len(client.guilds)
    print(serverss)
    print("Bot is ready")
    discord_terminal = client.get_channel(776117712074047539) 
    await discord_terminal.send(f'Bot is ready\nI am in {serverss} servers')
    dev_terminal = client.get_channel(869354307328307230) 
    await dev_terminal.send(f'Bot is ready\nI am in {serverss} servers')

    server_count = client.get_channel(869587186318716959)
    await server_count.edit(name=f'{len(client.guilds)} - Servers')

    # dbd.openDash(client)

@client.event
async def on_command_error(ctx, error):
    discord_error_terminal = dis.e_terminal(client)
    second_discord_error_terminal = client.get_channel(869353526546038784)
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=dis.e_embed(100))

    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=dis.e_embed(117))

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=dis.e_embed(101))

    elif isinstance(error, commands.CheckFailure):
        await ctx.send(embed=dis.e_embed(101))

    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send(embed=dis.e_embed(102))

    elif isinstance(error, commands.RoleNotFound):
        await ctx.send(embed=dis.e_embed(103))

    elif isinstance(error, commands.CommandNotFound):
        channel_embed = discord.Embed(
        colour=discord.Colour.red(),
        description=f'**Error 109:** {error} in server {ctx.guild.name}'
        )
        await discord_error_terminal.send(embed=channel_embed)
        await second_discord_error_terminal.send(embed=channel_embed)

    elif isinstance(error, commands.DisabledCommand):
        await ctx.send(embed=dis.e_embed(110))

    elif isinstance(error, commands.TooManyArguments):
        await ctx.send(embed=dis.e_embed(111))

    elif isinstance(error, commands.MessageNotFound):
        channel_embed = discord.Embed(
        colour=discord.Colour.red(),
        description=f'**Error 112:** Message not found in server {ctx.guild.name}'
        )
        await discord_error_terminal.send(embed=channel_embed)
        await second_discord_error_terminal.send(embed=channel_embed)

    elif isinstance(error, commands.UserNotFound):
        channel_embed = discord.Embed(
        colour=discord.Colour.red(),
        description=f'**Error 113:** User not found in server {ctx.guild.name}'
        )
        await discord_error_terminal.send(embed=channel_embed)
        await second_discord_error_terminal.send(embed=channel_embed)

    elif isinstance(error, commands.ChannelNotReadable):
        await ctx.send(embed=dis.e_embed(114))

    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(embed=dis.e_embed(118))

    else:
        try:
            channel_id = ctx.channel.id
        except:
            channel_id = ' '
        await second_discord_error_terminal.send(f'Unknown error in server: {ctx.guild.name} ({ctx.guild.id})\n{error} {channel_id}')
        await discord_error_terminal.send(f'Unknown error in server: {ctx.guild.name} ({ctx.guild.id})\n{error} {channel_id}')


@client.command(aliases=['botinfo','stats','Stats','stat','Stat'])
async def Botinfo(ctx):
    Info_embed =  discord.Embed(colour=discord.Color.blue(),title='__**Bot Info**__')

    #Ram Usage
    process = psutil.Process(os.getpid())
    mem = virtual_memory()
    num = (process.memory_info().rss / 1024 ** 3)/(mem.total / 1024 ** 3)
    Info_embed.add_field(name='__**RAM**__', value=f'Currently using **{round(process.memory_info().rss / 1024 ** 2,2)}MB** of RAM out of a total of **{round(mem.total / 1024 ** 3,2)}GB** \n**{round(num*100,2)}%** used', inline=False)
    #Uptime
    total_uptime = uptime(time.time())
    Info_embed.add_field(name='__**Uptime**__',value=f'{total_uptime}',inline=False)
    #Servernum
    Info_embed.add_field(name='__**Server Count**__',value=f'VC Roles is in {len(client.guilds)} servers', inline=False)
    #Bot Version
    Info_embed.add_field(name='__**Current Bot Version**__', value='Bot Version - 1.5',inline=False)
    #Guild Prefix
    Info_embed.add_field(name='__**Server Prefix**__',value=f'The Current Prefix for this server is **{dis.get_prefix(ctx.message)}**',inline=False)
    #Guild Shard
    shard_info = client.get_shard(0)
    shard_id = shard_info.id 
    shard_count = shard_info.shard_count
    Info_embed.add_field(name='__**Shard Info**__', value=f'Shard {shard_id}/{shard_count}')
    #Authors
    Info_embed.add_field(name='__**Authors**__',value=f'**cde#0001** and **SamHartland#9376**',inline=False)
    #PFP
    Info_embed.set_author(name=f'VC Roles#6632',icon_url='https://cdn.discordapp.com/attachments/758392649979265028/806279102330830858/circlemusicsoundspeakervolumeicon-1320196704838854001.png')


    await ctx.send(embed=Info_embed)

    dis.counter('stat')


# Cog Commands


@client.command()
@commands.check(dis.is_it_dev)
async def load(ctx, extension):
    try:
        client.load_extension(f'cogs.{extension}')
        await ctx.send(f'Successfully loaded {extension}')
    except:
        await ctx.send(f'Failed while loading {extension}')

@client.command()
@commands.check(dis.is_it_dev)
async def unload(ctx, extension):
    try:
        client.unload_extension(f'cogs.{extension}')
        await ctx.send(f'Successfully unloaded {extension}')
    except:
        await ctx.send(f'Failed while unloading {extension}')

@client.command()
@commands.check(dis.is_it_dev)
async def reload(ctx, extension):
    try:
        client.unload_extension(f'cogs.{extension}')
        await ctx.send(f'Successfully unloaded {extension}')
    except:
        await ctx.send(f'Failed while unloading {extension}')
    try:
        client.load_extension(f'cogs.{extension}')
        await ctx.send(f'Successfully loaded {extension}')
    except:
        await ctx.send(f'Failed while loading {extension}')


# Token and Running 


for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

client.run(bot_token)

