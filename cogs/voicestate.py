import discord
from discord.ext import commands
from bot import MyClient
from voicestate import all, category, logging, stage, voice, permanent

class voicestate(commands.Cog):
    
    def __init__(self, client: MyClient):
        self.client = client
        self.all = all.all(self)
        self.category = category.category(self)
        self.logging = logging.logging(self.client)
        self.stage = stage.stage(self)
        self.voice = voice.voice(self)
        self.permanent = permanent.perm(self.client)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot == True:
            return 

        # Joining
        if not before.channel and after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}')
            voice_added = stage_added = category_added = all_added = None

            if str(after.channel.type) == 'voice':
                voice_added = await self.voice.join(data, member, before, after)

            elif str(after.channel.type) == 'stage_voice':
                stage_added = await self.stage.join(data, member, before, after)

            category_added = await self.category.join(data, member, before, after)

            all_added = await self.all.join(data, member, before, after)

            perm_added = await self.permanent.join(data, member, before, after)

            await self.logging.log_join(after, member, voice_added, stage_added, category_added, all_added, perm_added)
            

        # Leaving
        elif before.channel and not after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}')
            voice_removed = stage_removed = category_removed = all_removed = None

            if str(before.channel.type) == 'voice':
                voice_removed = await self.voice.leave(data, member, before, after)

            elif str(before.channel.type) == 'stage_voice':
                stage_removed = await self.stage.leave(data, member, before, after)

            category_removed = await self.category.leave(data, member, before, after)

            all_removed = await self.all.leave(data, member, before, after)

            await self.logging.log_leave(before, member, voice_removed, stage_removed, category_removed, all_removed)

        # Changing
        elif before.channel != after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}')
            voice_removed = stage_removed = category_removed = all_removed = None
            voice_added = stage_added = category_added = all_added = None
            
            # Removing
            if str(before.channel.type) == 'voice':
                voice_removed = await self.voice.leave(data, member, before, after)

            elif str(before.channel.type) == 'stage_voice':
                stage_removed = await self.stage.leave(data, member, before, after)

            category_removed = await self.category.leave(data, member, before, after)

            _v = await self.all.leave(data, member, before, after)

            # Adding
            if str(after.channel.type) == 'voice':
                voice_added = await self.voice.join(data, member, before, after)

            elif str(after.channel.type) == 'stage_voice':
                stage_added = await self.stage.join(data, member, before, after)

            category_added = await self.category.join(data, member, before, after)

            _v = await self.all.join(data, member, before, after)

            await self.logging.log_change(before, after, member, voice_removed, stage_removed, category_removed, voice_added, stage_added, category_added)
        

def setup(client):
    client.add_cog(voicestate(client))