import discord, json, os
from discord.ext import commands

from voicestate import all, category, logging, stage, voice

with open('Data/config.json', 'r') as f:
    config = json.load(f)

class MyClient(commands.AutoShardedBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.all = all.all(self)
        self.category = category.category(self)
        self.logging = logging.logging(self)
        self.stage = stage.stage(self)
        self.voice = voice.voice(self)
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print(f'Bot is in {len(self.guilds)} guilds.')
        print('------')

        await client.change_presence(status=discord.Status.online)
        await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching,name='Voice Channels - ?help'))

        # discord_terminal = client.get_channel(776117712074047539) 
        # await discord_terminal.send(f'Bot is ready\nI am in {serverss} servers')
        # dev_terminal = client.get_channel(869354307328307230) 
        # await dev_terminal.send(f'Bot is ready\nI am in {serverss} servers')

        # server_count = client.get_channel(869587186318716959)
        # await server_count.edit(name=f'{len(client.guilds)} - Servers')

    async def on_guild_join(self, guild:discord.Guild):
        with open('Data/guild_data.json', 'r') as f:
            data = json.load(f)
        
        data[str(guild.id)] = {'tts': {'enabled': False, 'role': None},'logging': None}

        with open('Data/guild_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    async def on_guild_remove(self, guild:discord.Guild):
        with open('Data/guild_data.json', 'r') as f:
            data = json.load(f)

        try:
            data.pop(str(guild.id))

            with open('Data/guild_data.json', 'w') as f:
                json.dump(data, f, indent=4)
        except:
            pass

intents = discord.Intents(messages = True, guilds = True, reactions = True, voice_states = True)

client = MyClient('!', intents=intents)


# COMMANDS

# Cog Commands
@client.slash_command(guild_ids=[758392649979265024])
async def load(ctx, extension:str):
    try:
        client.load_extension(f'cogs.{extension}')
        await ctx.respond(f'Successfully loaded {extension}')
    except:
        await ctx.respond(f'Failed while loading {extension}')

@client.slash_command(guild_ids=[758392649979265024])
async def unload(ctx, extension:str):
    try:
        client.unload_extension(f'cogs.{extension}')
        await ctx.respond(f'Successfully unloaded {extension}')
    except:
        await ctx.respond(f'Failed while unloading {extension}')

@client.slash_command(guild_ids=[758392649979265024])
async def reload(ctx, extension: str):
    try:
        client.unload_extension(f'cogs.{extension}')
        await ctx.respond(f'Successfully unloaded {extension}')
    except:
        await ctx.respond(f'Failed while unloading {extension}')
    try:
        client.load_extension(f'cogs.{extension}')
        await ctx.channel.send(f'Successfully loaded {extension}')
    except:
        await ctx.channel.send(f'Failed while loading {extension}')

# Adding Extensions

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')
        print(f'Loaded extension: {filename[:-3]}')

# Running the bot.

client.run(config['TESTING_TOKEN'])