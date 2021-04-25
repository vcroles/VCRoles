import discord
from discord.ext import commands
from ds import ds
dis = ds()

class vccontrol(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['Vcmute'])
    @commands.has_permissions(administrator=True)
    async def vcmute(self, ctx, choice='me'):

        try:
            choice = int(choice)
            this = 1
        except:
            this = 0

        if choice == 'all':
            vc = ctx.author.voice.channel
            for member in vc.members:
                await member.edit(mute=True)
            embed_description = 'everyone'
        
        elif choice == 'me':
            vc = ctx.author.voice.channel
            for member in vc.members:
                if member == ctx.author:
                    pass
                else:
                    await member.edit(mute=True)
            embed_description = 'everyone but you'

        elif this == 1:
            vc = self.client.get_channel(choice)
            for member in vc.members:
                await member.edit(mute=True)
            embed_description = 'everyone'
        
        else:
            await ctx.send(dis.e_embed(100))


        mute_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Muted {embed_description} in voice channel {vc.name}'
        )
        await ctx.send(embed=mute_embed)

        dis.counter('vcmute')

    @commands.command(aliases=['Vcdeafen'])
    @commands.has_permissions(administrator=True)
    async def vcdeafen(self, ctx, choice='me'):
        try:
            choice = int(choice)
            this = 1
        except:
            this = 0

        if choice == 'all':
            vc = ctx.author.voice.channel
            for member in vc.members:
                await member.edit(deafen=True)
            embed_description = 'everyone'
        
        elif choice == 'me':
            vc = ctx.author.voice.channel
            for member in vc.members:
                if member == ctx.author:
                    pass
                else:
                    await member.edit(deafen=True)
            embed_description = 'everyone but you'

        elif this == 1:
            vc = self.client.get_channel(choice)
            for member in vc.members:
                await member.edit(deafen=True)
            embed_description = 'everyone'

        deafen_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Deafened {embed_description} in voice channel {vc.name}'
        )
        await ctx.send(embed=deafen_embed)

        dis.counter('vcdeafen')

    @commands.command(aliases=['Vcunmute'])
    @commands.has_permissions(administrator=True)
    async def vcunmute(self, ctx, choice='all'):
        try:
            choice = int(choice)
            this = 1
        except:
            this = 0
        
        if choice == 'all':
            vc = ctx.author.voice.channel
            for member in vc.members:
                await member.edit(mute=False)

        elif this == 1:
            vc = self.client.get_channel(choice)
            for member in vc.members:
                await member.edit(mute=False)

        unmute_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Unmuted everyone in voice channel {vc.name}'
        )
        await ctx.send(embed=unmute_embed)

        dis.counter('vcunmute')

    @commands.command(aliases=['Vcundeafen','vcundeaf'])
    @commands.has_permissions(administrator=True)
    async def vcundeafen(self, ctx, choice='all'):
        try:
            choice = int(choice)
            this = 1
        except:
            this = 0
        
        if choice == 'all':
            vc = ctx.author.voice.channel
            for member in vc.members:
                await member.edit(deafen=False)

        elif this == 1:
            vc = self.client.get_channel(choice)
            for member in vc.members:
                await member.edit(deafen=False)

        undeafen_embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f'Undeafened everyone in voice channel {vc.name}'
        )
        await ctx.send(embed=undeafen_embed)

        dis.counter('vcundeafen')

def setup(client):
    client.add_cog(vccontrol(client))