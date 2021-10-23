import discord
from discord.ext import commands
from bot import MyClient
from voicestate import all, category, logging, stage, voice, permanent, generator

class voicestate(commands.Cog):
    
    def __init__(self, client: MyClient):
        self.client = client
        self.all = all.all(self)
        self.category = category.category(self)
        self.logging = logging.logging(self.client)
        self.stage = stage.stage(self)
        self.voice = voice.voice(self)
        self.permanent = permanent.perm(self.client)
        self.generator = generator.generator(self.client)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot == True:
            return 

        # Joining
        if not before.channel and after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}', str(member.guild.id))
            voice_added = stage_added = category_added = all_added = None

            if str(after.channel.type) == 'voice':
                try:
                    voice_added = await self.voice.join(data, member, before, after)
                except:
                    voice_added = None

            elif str(after.channel.type) == 'stage_voice':
                try:
                    stage_added = await self.stage.join(data, member, before, after)
                except:
                    stage_added = None

            try:
                category_added = await self.category.join(data, member, before, after)
            except:
                category_added = None

            try:
                all_added = await self.all.join(data, member, before, after)
            except:
                all_added = None

            try:
                perm_added = await self.permanent.join(data, member, before, after)
            except:
                perm_added = None

            try:
                await self.generator.join(member, before, after)
            except:
                pass

            await self.logging.log_join(after, member, voice_added, stage_added, category_added, all_added, perm_added)
            

        # Leaving
        elif before.channel and not after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}', str(member.guild.id))
            voice_removed = stage_removed = category_removed = all_removed = None

            if str(before.channel.type) == 'voice':
                try:
                    voice_removed = await self.voice.leave(data, member, before, after)
                except:
                    voice_removed = None

            elif str(before.channel.type) == 'stage_voice':
                try:
                    stage_removed = await self.stage.leave(data, member, before, after)
                except:
                    stage_removed = None

            try:
                category_removed = await self.category.leave(data, member, before, after)
            except:
                category_removed = None

            try:
                all_removed = await self.all.leave(data, member, before, after)
            except:
                all_removed = None

            try:
                await self.generator.leave(member, before, after)
            except:
                pass

            await self.logging.log_leave(before, member, voice_removed, stage_removed, category_removed, all_removed)

        # Changing
        elif before.channel != after.channel:
            data = self.client.jopen(f'Linked/{member.guild.id}', str(member.guild.id))
            voice_removed = stage_removed = category_removed = all_removed = None
            voice_added = stage_added = category_added = all_added = None
            
            # Removing
            if str(before.channel.type) == 'voice':
                try:
                    voice_removed = await self.voice.leave(data, member, before, after)
                except:
                    voice_removed = None

            elif str(before.channel.type) == 'stage_voice':
                try:
                    stage_removed = await self.stage.leave(data, member, before, after)
                except:
                    stage_removed = None

            try:
                category_removed = await self.category.leave(data, member, before, after)
            except:
                category_removed = None

            try:
                all_removed = await self.all.leave(data, member, before, after)
            except:
                all_removed = None

            try:
                await self.generator.leave(member, before, after)
            except:
                pass

            # Adding
            if str(after.channel.type) == 'voice':
                try:
                    voice_added = await self.voice.join(data, member, before, after)
                except:
                    voice_added = None

            elif str(after.channel.type) == 'stage_voice':
                try:
                    stage_added = await self.stage.join(data, member, before, after)
                except:
                    stage_added = None

            try:
                category_added = await self.category.join(data, member, before, after)
            except:
                category_added = None

            try:
                all_added = await self.all.join(data, member, before, after)
            except:
                all_added = None

            try:
                perm_added = await self.permanent.join(data, member, before, after)
            except:
                perm_added = None

            try:
                await self.generator.join(member, before, after)
            except:
                pass

            await self.logging.log_change(before, after, member, voice_removed, stage_removed, category_removed, voice_added, stage_added, category_added)
        

def setup(client):
    client.add_cog(voicestate(client))