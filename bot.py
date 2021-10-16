import discord, json, os
from discord.ext import commands

with open('Data/config.json', 'r') as f:
    config = json.load(f)

class MyClient(commands.AutoShardedBot):

    def jopen(self, file):
        with open(f'{file}.json', 'r') as f:
            return json.load(f)
    
    def jdump(self, file, data):
        with open(f'{file}.json', 'w') as f:
            json.dump(data, f, indent=4)
    
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
        data = self.jopen('Data/guild_data')
        
        data[str(guild.id)] = {'tts': {'enabled': False, 'role': None},'logging': None}

        self.jdump('Data/guild_data', data)

    async def on_guild_remove(self, guild:discord.Guild):
        data = self.jopen('Data/guild_data')

        try:
            data.pop(str(guild.id))

            self.jdump('Data/guild_data', data)
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
        client.reload_extension(f'cogs.{extension}')
        await ctx.respond(f'Successfully reloaded {extension}')
    except:
        await ctx.respond(f'Failed while reloading {extension}')

# Adding Extensions

for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')
        print(f'Loaded extension: {filename[:-3]}')

# Running the bot.

client.run(config['TESTING_TOKEN'])