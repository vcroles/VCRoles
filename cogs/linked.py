import discord
from discord import ApplicationContext
from discord.ext import commands
from bot import MyClient

class linkedC(commands.Cog):

    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description='Displays the linked roles, channels & categories', guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def linked(self, ctx: ApplicationContext):
        data = self.client.jopen(f'Linked/{ctx.guild.id}', str(ctx.guild.id))

        linked_embed = discord.Embed(colour=discord.Colour.blue(), title=f'The linked roles, channels & categories in {ctx.guild.name}:')
        va = ''

        v_dict = data['voice']

        for v_list in v_dict:
            channel = self.client.get_channel(int(v_list))
            va += f'{channel.mention}: '
            for role in v_dict[v_list]:
                role = ctx.guild.get_role(int(role))
                va += f'{role.mention} '
            va += '\n'

        s_dict = data['stage']

        for s_list in s_dict:
            channel = self.client.get_channel(int(s_list))
            va += f'{channel.mention}: '
            for role in s_dict[s_list]:
                role = ctx.guild.get_role(int(role))
                va += f'{role.mention} '
            va += '\n'

        c_dict = data['category']

        for c_list in c_dict:
            channel = self.client.get_channel(int(c_list))
            va += f'Category {channel.mention}: '
            for role in c_dict[c_list]:
                role = ctx.guild.get_role(int(role))
                va += f'{role.mention} '
            va += '\n'

        p_dict = data['permanent']

        for p_list in p_dict:
            channel = self.client.get_channel(int(p_list))
            va += f'Permanent {channel.mention}: '
            for role in p_dict[p_list]:
                role = ctx.guild.get_role(int(role))
                va += f'{role.mention} '
            va += '\n'

        a_list = data['all']['roles']
        if a_list:
            va += 'All: '
            for role in a_list:
                role = ctx.guild.get_role(int(role))
                va += f'{role.mention} '
            va += '\n'
        a_list_e = data['all']['except']
        if a_list_e:
            va += 'All-link exceptions: '
            for channel in a_list_e:
                channel = self.client.get_channel(int(channel))
                va += f'{channel.mention} '
            va += '\n'

        if va:
            va = va[:-1]
            linked_embed.add_field(name='Linked:', value=va)
            await ctx.respond(embed=linked_embed)
        else:
            await ctx.respond('Nothing is linked')


def setup(client):
    client.add_cog(linkedC(client))