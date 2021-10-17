import discord
from discord.ext import commands
from discord.app.commands import Option
from bot import MyClient

class alllink(commands.Cog):
    
    def __init__(self, client):
        self.client = client

    @commands.slash_command(description='Use to link all channels with a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def alllink(self, ctx: discord.ApplicationContext, role: Option(discord.Role,'Select a role to link', required=True)):
            
        data = self.client.jopen(f'Linked/{ctx.guild.id}')

        if str(role.id) not in data['all']:
            data['all'].append(str(role.id))

            self.client.jdump(f'Linked/{ctx.guild.id}', data)
            
            await ctx.respond(f'Linked all channels with role: `@{role.name}`')

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f'Please ensure my highest role is above `@{role.name}`')
        else:
            await ctx.respond(f'The channel and role are already linked.')


    @commands.slash_command(description='Use to unlink all channels from a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def allunlink(self, ctx: discord.ApplicationContext, role: Option(discord.Role,'Select a role to link', required=True)):
            
        data = self.client.jopen(f'Linked/{ctx.guild.id}')

        if str(role.id) in data['all']:
            try:
                data['all'].remove(str(role.id))

                self.client.jdump(f'Linked/{ctx.guild.id}', data)

                await ctx.respond(f'Unlinked all channels from role: `@{role.name}`')
            except:
                pass
        else:
            await ctx.respond(f'The channel and role are not linked.')

def setup(client):
    client.add_cog(alllink(client))