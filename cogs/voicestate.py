import discord
from discord.ext import commands
from bot import MyClient
from voicestate import all, category, logging, stage, voice

class voicestate(commands.Cog):
    
    def __init__(self, client: MyClient):
        self.client = client
        self.all = all.all(self)
        self.category = category.category(self)
        self.logging = logging.logging(self)
        self.stage = stage.stage(self)
        self.voice = voice.voice(self)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot == True:
            return 
        print(member)
        # logging_embed = discord.Embed()
        
        


def setup(client):
    client.add_cog(voicestate(client))