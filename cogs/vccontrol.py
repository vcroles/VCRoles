from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class VCControl(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    control_commands = app_commands.Group(
        name="vc", description="Used to control voice channels"
    )

    async def get_members(self, interaction: discord.Interaction):
        mem = []
        for user_id, state in interaction.guild._voice_states.items():
            if (
                state.channel == interaction.user.voice.channel
                or state.channel.id == interaction.user.voice.channel.id
            ):
                mem.append(await interaction.guild.fetch_member(user_id))
        return mem

    @control_commands.command(description="Mutes everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(who="Who to mute:")
    async def mute(
        self,
        interaction: discord.Interaction,
        who: Optional[Literal["everyone", "everyone but me"]] = "everyone but me",
    ):
        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if who == "everyone" and vc:
            for member in mem:
                await member.edit(mute=True)
        elif who == "everyone but me" and vc:
            for member in vc.members:
                if member == interaction.user:
                    pass
                else:
                    await member.edit(mute=True)
        else:
            await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully muted in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        return self.client.incr_counter("vc_mute")

    @control_commands.command(description="Deafens everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(who="Who to deafen:")
    async def deafen(
        self,
        interaction: discord.Interaction,
        who: Optional[Literal["everyone", "everyone but me"]] = "everyone but me",
    ):
        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if who == "everyone" and vc:
            for member in mem:
                await member.edit(deafen=True)
        elif who == "everyone but me" and vc:
            for member in vc.members:
                if member == interaction.user:
                    pass
                else:
                    await member.edit(deafen=True)
        else:
            await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully deafened in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        return self.client.incr_counter("vc_deafen")

    @control_commands.command(description="Unmutes everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    async def unmute(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if vc:
            for member in mem:
                await member.edit(mute=False)
        else:
            await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully unmuted in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        return self.client.incr_counter("vc_unmute")

    @control_commands.command(description="Undeafens everyone in a voice channel")
    @Permissions.has_permissions(administrator=True)
    async def undeafen(self, interaction: discord.Interaction):
        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if vc:
            for member in mem:
                await member.edit(deafen=False)
        else:
            await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )
            return

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully undeafened in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        return self.client.incr_counter("vc_undeafen")


async def setup(client: MyClient):
    await client.add_cog(VCControl(client))
