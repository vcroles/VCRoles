import discord
from discord.ext import commands
from bot import MyClient


class voicestate(commands.Cog):
    
    def __init__(self, client: MyClient):
        self.client = client

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot == True:
            return 
        print(member)
        # logging_embed = discord.Embed()
        


def setup(client):
    client.add_cog(voicestate(client))