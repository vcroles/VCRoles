import discord
from discord.commands import Option
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class VCControl(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    async def get_members(self, ctx):
        mem = []
        for user_id, state in ctx.guild._voice_states.items():
            if (
                state.channel == ctx.author.voice.channel
                or state.channel.id == ctx.author.voice.channel.id
            ):
                mem.append(await ctx.guild.fetch_member(user_id))
        return mem

    @commands.slash_command(description="Mutes everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    async def vcmute(
        self,
        ctx: discord.ApplicationContext,
        who: Option(
            str,
            "Who to mute?",
            choices=["everyone", "everyone but me"],
            default="everyone but me",
        ),
    ):
        if ctx.author.voice and ctx.author.voice.channel:
            vc = ctx.author.voice.channel

        mem = await self.get_members(ctx)

        if who == "everyone" and vc:
            for member in mem:
                await member.edit(mute=True)
        elif who == "everyone but me" and vc:
            for member in vc.members:
                if member == ctx.author:
                    pass
                else:
                    await member.edit(mute=True)
        else:
            await ctx.respond("Please ensure you are in a voice channel.")
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully muted in {vc.mention}",
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(description="Deafens everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    async def vcdeafen(
        self,
        ctx: discord.ApplicationContext,
        who: Option(
            str,
            "Who to mute?",
            choices=["everyone", "everyone but me"],
            default="everyone but me",
        ),
    ):
        if ctx.author.voice and ctx.author.voice.channel:
            vc = ctx.author.voice.channel

        mem = await self.get_members(ctx)

        if who == "everyone" and vc:
            for member in mem:
                await member.edit(deafen=True)
        elif who == "everyone but me" and vc:
            for member in vc.members:
                if member == ctx.author:
                    pass
                else:
                    await member.edit(deafen=True)
        else:
            await ctx.respond("Please ensure you are in a voice channel.")
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully deafened in {vc.mention}",
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(description="Unmutes everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    async def vcunmute(self, ctx: discord.ApplicationContext):
        if ctx.author.voice and ctx.author.voice.channel:
            vc = ctx.author.voice.channel

        mem = await self.get_members(ctx)

        if vc:
            for member in mem:
                await member.edit(mute=False)
        else:
            await ctx.respond("Please ensure you are in a voice channel.")
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully unmuted in {vc.mention}",
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(description="Undeafens everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    async def vcundeafen(self, ctx: discord.ApplicationContext):
        if ctx.author.voice and ctx.author.voice.channel:
            vc = ctx.author.voice.channel

        mem = await self.get_members(ctx)

        if vc:
            for member in mem:
                await member.edit(deafen=False)
        else:
            await ctx.respond("Please ensure you are in a voice channel.")
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully undeafened in {vc.mention}",
        )
        await ctx.respond(embed=embed)


def setup(client: MyClient):
    client.add_cog(VCControl(client))
