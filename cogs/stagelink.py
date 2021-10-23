import discord
from discord.commands import Option
from discord.ext import commands
from bot import MyClient

class stagelink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description='Use to link a stage channel with a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def stagelink(self, ctx: discord.ApplicationContext, channel: Option(discord.StageChannel, 'Select a stage channel to link', required=True), role: Option(discord.Role,'Select a role to link', required=True)):
        data = self.client.jopen(f'Linked/{ctx.guild.id}', str(ctx.guild.id))

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

    
    @commands.slash_command(description='Use to unlink a stage channel from a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def stageunlink(self, ctx: discord.ApplicationContext, channel: Option(discord.StageChannel, 'Select a stage channel to link', required=True), role: Option(discord.Role,'Select a role to link', required=True)):
        data = self.client.jopen(f'Linked/{ctx.guild.id}', str(ctx.guild.id))

        try:
            data['stage'][str(channel.id)]
        except:
            await ctx.respond(f'The channel and role are not linked.')
            return

        if str(role.id) in data['stage'][str(channel.id)]:
            try:
                data['stage'][str(channel.id)].remove(str(role.id))

                if not data['stage'][str(channel.id)]:
                    data['stage'].pop(str(channel.id))

                self.client.jdump(f'Linked/{ctx.guild.id}', data)

                await ctx.respond(f'Unlinked {channel.mention} and role: `@{role.name}`')
            except:
                pass
        

def setup(client):
    client.add_cog(stagelink(client))