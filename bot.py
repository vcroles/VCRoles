import discord, json

with open('Data/config.json', 'r') as f:
    config = json.load(f)

class MyClient(discord.AutoShardedBot):
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print(f'Bot is in {len(self.guilds)}')
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
        
        data[str(guild.id)] = {'prefix': '?', 'tts': {'enabled': False, 'role': None},'logging': None}

        with open('Data/guild_data.json', 'w') as f:
            json.dump(data, f, indent=4)

    async def on_guild_remove(self, guild:discord.Guild):
        with open('Data/guild_data.json', 'r') as f:
            data = json.load(f)

        data.pop(str(guild.id))

        with open('Data/guild_data.json', 'w') as f:
            json.dump(data, f, indent=4)

intents = discord.Intents(messages = True, guilds = True, reactions = True, voice_states = True)

client = MyClient(intents=intents)



# COMMANDS

@client.slash_command(guild_ids=[758392649979265024])
async def load(ctx, extension:str):
    try:
        client.load_extension(f'cogs.{extension}')
        await ctx.send(f'Successfully loaded {extension}')
    except:
        await ctx.send(f'Failed while loading {extension}')

@client.slash_command(guild_ids=[758392649979265024])
async def unload(ctx, extension:str):
    try:
        client.unload_extension(f'cogs.{extension}')
        await ctx.send(f'Successfully unloaded {extension}')
    except:
        await ctx.send(f'Failed while unloading {extension}')


client.run(config['TESTING_TOKEN'])