import discord
from discord.app.commands import Option
from discord.ext import commands
from bot import MyClient

class vccontrol(commands.Cog):

    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description='Mutes everyone in a voice channel', guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def vcmute(self, ctx: discord.ApplicationContext, who: Option(str, 'Who to mute?', choices=['everyone', 'everyone but me'], default='everyone but me')):
        if ctx.author.voice and ctx.author.voice.channel:
            vc = ctx.author.voice.channel
        # Problem with the library, not the code (i think) :(
        mem =[]
        for user_id, state in ctx.guild._voice_states.items():
            if state.channel == ctx.author.voice.channel or state.channel.id == ctx.author.voice.channel.id:
                mem.append(user_id)
        print(mem)

        if who == 'everyone' and vc:
            print(vc, vc.members)
            for member in mem:
                member = ctx.guild.get_member(member)
                await member.edit(mute=True)
            embed = discord.Embed(colour=discord.Colour.dark_grey(), description=f'Successfully muted in {vc.mention}')
            await ctx.respond(embed=embed)
        elif who == 'everyone but me' and vc:
            for member in vc.members:
                if member == ctx.author:
                    pass
                else:
                    await member.edit(mute=True)
            embed = discord.Embed(colour=discord.Colour.dark_grey(), description=f'Successfully muted in {vc.mention}')
            await ctx.respond(embed=embed)
        else:
            await ctx.respond('Please ensure you are in a voice channel.')
            return
        

    @commands.slash_command(description='Deafens everyone in a voice channel', guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def vcdeafen(self, ctx: discord.ApplicationContext, who: Option(str, 'Who to mute?', choices=['everyone', 'everyone but me'], default='everyone but me')):
        member = ctx.guild.get_member(ctx.author.id)
        vc = member.voice.channel
        
        if who == 'everyone' and vc:
            for member in vc.members:
                await member.edit(deafen=True)
        elif who == 'everyone but me' and vc:
            for member in vc.members:
                if member == ctx.author:
                    pass
                else:
                    await member.edit(deafen=True)
        else:
            await ctx.respond('Please ensure you are in a voice channel.')
            return
        
        embed = discord.Embed(colour=discord.Colour.dark_grey(), description=f'Successfully deafened in {vc.mention}')
        await ctx.respond(embed=embed)

    @commands.slash_command(description='Unmutes everyone in a voice channel', guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def vcunmute(self, ctx: discord.ApplicationContext):
        member = ctx.guild.get_member(ctx.author.id)
        vc = member.voice.channel

        if vc:
            for member in vc.members:
                await member.edit(mute=False)
        else:
            await ctx.respond('Please ensure you are in a voice channel.')
            return
        
        embed = discord.Embed(colour=discord.Colour.dark_grey(), description=f'Successfully unmuted in {vc.mention}')
        await ctx.respond(embed=embed)

    @commands.slash_command(description='Undeafens everyone in a voice channel', guild_ids=[758392649979265024])
    @commands.has_permissions(administrator=True)
    async def vcundeafen(self, ctx: discord.ApplicationContext):
        member = ctx.guild.get_member(ctx.author.id)
        vc = member.voice.channel

        if vc:
            for member in vc.members:
                await member.edit(deafen=False)
        else:
            await ctx.respond('Please ensure you are in a voice channel.')
            return
        
        embed = discord.Embed(colour=discord.Colour.dark_grey(), description=f'Successfully undeafened in {vc.mention}')
        await ctx.respond(embed=embed)

def setup(client):
    client.add_cog(vccontrol(client))