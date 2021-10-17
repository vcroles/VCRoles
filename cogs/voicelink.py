import discord
from discord.ext import commands
from bot import MyClient

class voicelink(commands.Cog):

    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description='Use to link a voice/stage channel with a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def vclink(self, ctx: discord.ApplicationContext, channel: discord.abc.GuildChannel, role: discord.Role):
        if str(channel.type) == 'voice':
            
            data = self.client.jopen(f'Linked/{ctx.guild.id}')

            try:
                data['voice'][str(channel.id)]
            except:
                data['voice'][str(channel.id)] = []

            if str(role.id) not in data['voice'][str(channel.id)]:
                data['voice'][str(channel.id)].append(str(role.id))

                self.client.jdump(f'Linked/{ctx.guild.id}', data)
                
                await ctx.respond(f'Linked {channel.mention} with role: `@{role.name}`')

                member = ctx.guild.get_member(self.client.user.id)
                if member.top_role.position < role.position:
                    await ctx.send(f'Please ensure my highest role is above `@{role.name}`')
            else:
                await ctx.respond(f'The channel and role are already linked.')

        elif str(channel.type) == 'stage_voice':

            data = self.client.jopen(f'Linked/{ctx.guild.id}')

            try:
                data['stage'][str(channel.id)]
            except:
                data['stage'][str(channel.id)] = []

            if str(role.id) not in data['stage'][str(channel.id)]:
                data['stage'][str(channel.id)].append(str(role.id))

                self.client.jdump(f'Linked/{ctx.guild.id}', data)
                
                await ctx.respond(f'Linked {channel.mention} with role: `@{role.name}`')

                member = ctx.guild.get_member(self.client.user.id)
                if member.top_role.position < role.position:
                    await ctx.send(f'Please ensure my highest role is above `@{role.name}`')
            else:
                await ctx.respond(f'The channel and role are already linked.')

        else:
            await ctx.respond(f'Please select either a stage, or voice channel')

    @commands.slash_command(description='Use to unlink a voice/stage channel from a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def vcunlink(self, ctx: discord.ApplicationContext, channel: discord.abc.GuildChannel, role: discord.Role):
        if str(channel.type) == 'voice':
            
            data = self.client.jopen(f'Linked/{ctx.guild.id}')

            if str(role.id) in data['voice'][str(channel.id)]:
                try:
                    data['voice'][str(channel.id)].remove(str(role.id))
                    
                    if not data['voice'][str(channel.id)]:
                        data['voice'].pop(str(channel.id))

                    self.client.jdump(f'Linked/{ctx.guild.id}', data)

                    await ctx.respond(f'Unlinked {channel.mention} and role: `@{role.name}`')
                except:
                    pass
            else:
                await ctx.respond(f'The channel and role are not linked.')

        elif str(channel.type) == 'stage_voice':

            data = self.client.jopen(f'Linked/{ctx.guild.id}')

            if str(role.id) in data['stage'][str(channel.id)]:
                try:
                    data['stage'][str(channel.id)].remove(str(role.id))

                    if not data['stage'][str(channel.id)]:
                        data['stage'].pop(str(role.id))

                    self.client.jdump(f'Linked/{ctx.guild.id}', data)

                    await ctx.respond(f'Unlinked {channel.mention} and role: `@{role.name}`')
                except:
                    pass
            else:
                await ctx.respond(f'The channel and role are not linked.')

        else:
            await ctx.respond(f'Please select either a stage, or voice channel')

def setup(client):
    client.add_cog(voicelink(client))