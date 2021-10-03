import discord, json

with open('Data/config.json', 'r') as f:
    config = json.load(f)

class MyClient(discord.AutoShardedBot):
    
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        print('------')

    async def on_guild_join(self, guild:discord.Guild):
        with open('Data/guild_data.json', 'r') as f:
            data = json.load(f)
        
        data[str(guild.id)] = {'prefix': '?', 'tts': {'enabled': False, 'role': None},'logging': None}

intents = discord.Intents(messages = True, guilds = True, reactions = True, voice_states = True)

client = MyClient(intents=intents)



client.run(config['TESTING_TOKEN'])