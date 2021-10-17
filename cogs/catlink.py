import discord
from discord.ext import commands
from discord.app.commands import Option
from bot import MyClient

class catlink(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.slash_command(description='Use to link all channels in a category with a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def catlink(self, ctx: discord.ApplicationContext, channel: Option(discord.CategoryChannel, 'Select a category to link', required=True), role: Option(discord.Role,'Select a role to link', required=True)):
            
        data = self.client.jopen(f'Linked/{ctx.guild.id}')

        try:
            data['category'][str(channel.id)]
        except:
            data['category'][str(channel.id)] = []

        if str(role.id) not in data['category'][str(channel.id)]:
            data['category'][str(channel.id)].append(str(role.id))

            self.client.jdump(f'Linked/{ctx.guild.id}', data)
            
            await ctx.respond(f'Linked {channel.mention} with role: `@{role.name}`')

            member = ctx.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await ctx.send(f'Please ensure my highest role is above `@{role.name}`')
        else:
            await ctx.respond(f'The channel and role are already linked.')


    @commands.slash_command(description='Use to unlink a category from a role',guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def catunlink(self, ctx: discord.ApplicationContext, channel: Option(discord.CategoryChannel, 'Select a category to link', required=True), role: Option(discord.Role,'Select a role to link', required=True)):
            
        data = self.client.jopen(f'Linked/{ctx.guild.id}')

        if str(role.id) in data['category'][str(channel.id)]:
            try:
                data['category'][str(channel.id)].remove(str(role.id))
                
                if not data['category'][str(channel.id)]:
                    data['category'].pop(str(channel.id))

                self.client.jdump(f'Linked/{ctx.guild.id}', data)

                await ctx.respond(f'Unlinked {channel.mention} and role: `@{role.name}`')
            except:
                pass
        else:
            await ctx.respond(f'The channel and role are not linked.')

def setup(client):
    client.add_cog(catlink(client))