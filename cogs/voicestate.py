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

        # Joining
        if not before.channel and after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}')

            if str(after.channel.type) == 'voice':
                voice_added = await self.voice.join(data, member, before, after)

            elif str(after.channel.type) == 'stage_voice':
                stage_added = await self.stage.join(data, member, before, after)

            category_added = await self.category.join(data, member, before, after)

            all_added = await self.all.join(data, member, before, after)
            

        # Leaving
        elif before.channel and not after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}')

            if str(before.channel.type) == 'voice':
                voice_removed = await self.voice.leave(data, member, before, after)

            elif str(before.channel.type) == 'stage_voice':
                stage_removed = await self.stage.leave(data, member, before, after)

            category_removed = await self.category.leave(data, member, before, after)

            all_removed = await self.all.leave(data, member, before, after)

        # Changing
        elif before.channel != after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}')

            # Adding
            if str(after.channel.type) == 'voice':
                voice_added = await self.voice.join(data, member, before, after)

            elif str(after.channel.type) == 'stage_voice':
                stage_added = await self.stage.join(data, member, before, after)

            category_added = await self.category.join(data, member, before, after)
            
            # Removing
            if str(before.channel.type) == 'voice':
                voice_removed = await self.voice.leave(data, member, before, after)

            elif str(before.channel.type) == 'stage_voice':
                stage_removed = await self.stage.leave(data, member, before, after)

            category_removed = await self.category.leave(data, member, before, after)
        

def setup(client):
    client.add_cog(voicestate(client))