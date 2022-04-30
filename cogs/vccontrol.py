import asyncio
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient


class VCControl(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    control_commands = app_commands.Group(
        name="vc", description="Used to control voice channels"
    )

    async def get_members(
        self, interaction: discord.Interaction
    ) -> list[discord.Member]:
        mem = []
        for user_id, state in interaction.guild._voice_states.items():
            if state.channel and state.channel.id == interaction.user.voice.channel.id:
                member = await interaction.guild.fetch_member(user_id)
                if member is not None:
                    mem.append(member)
        return mem

    @control_commands.command()
    @app_commands.describe(who="Who to mute:")
    async def mute(
        self,
        interaction: discord.Interaction,
        who: Optional[Literal["everyone", "everyone but me"]] = "everyone but me",
    ):
        """Mutes everyone in a voice channel"""
        await self.client._has_permissions(interaction, administrator=True)

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if who == "everyone" and vc:
            tasks = [
                self.client.loop.create_task(member.edit(mute=True)) for member in mem
            ]
        elif who == "everyone but me" and vc:
            tasks = [
                self.client.loop.create_task(member.edit(mute=True))
                for member in mem
                if member.id != interaction.user.id
            ]
        else:
            return await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully muted in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        await asyncio.gather(*tasks)

        return self.client.incr_counter("vc_mute")

    @control_commands.command()
    @app_commands.describe(who="Who to deafen:")
    async def deafen(
        self,
        interaction: discord.Interaction,
        who: Optional[Literal["everyone", "everyone but me"]] = "everyone but me",
    ):
        """Deafens everyone in a voice channel"""
        await self.client._has_permissions(interaction, administrator=True)

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if who == "everyone" and vc:
            tasks = [
                self.client.loop.create_task(member.edit(deafen=True)) for member in mem
            ]
        elif who == "everyone but me" and vc:
            tasks = [
                self.client.loop.create_task(member.edit(deafen=True))
                for member in mem
                if member.id != interaction.user.id
            ]
        else:
            return await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully deafened in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        await asyncio.gather(*tasks)

        return self.client.incr_counter("vc_deafen")

    @control_commands.command()
    async def unmute(self, interaction: discord.Interaction):
        """Unmutes everyone in a voice channel"""
        await self.client._has_permissions(interaction, administrator=True)

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if vc:
            tasks = [
                self.client.loop.create_task(member.edit(mute=False)) for member in mem
            ]
        else:
            return await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully unmuted in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        await asyncio.gather(*tasks)

        return self.client.incr_counter("vc_unmute")

    @control_commands.command()
    async def undeafen(self, interaction: discord.Interaction):
        """Undeafens everyone in a voice channel"""
        await self.client._has_permissions(interaction, administrator=True)

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel

        mem = await self.get_members(interaction)

        if vc:
            tasks = [
                self.client.loop.create_task(member.edit(deafen=False))
                for member in mem
            ]
        else:
            return await interaction.response.send_message(
                "Please ensure you are in a voice channel."
            )

        embed = discord.Embed(
            colour=discord.Colour.dark_grey(),
            description=f"Successfully undeafened in {vc.mention}",
        )
        await interaction.response.send_message(embed=embed)

        await asyncio.gather(*tasks)

        return self.client.incr_counter("vc_undeafen")


async def setup(client: MyClient):
    await client.add_cog(VCControl(client))
