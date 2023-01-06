import asyncio
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from utils.types import LogLevel


class VCControl(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    control_commands = app_commands.Group(
        name="vc", description="Used to control voice channels"
    )

    @staticmethod
    async def get_members(
        guild: discord.Guild, user: discord.Member
    ) -> list[discord.Member]:
        mem: list[discord.Member] = []
        for user_id, state in guild._voice_states.items():  # type: ignore
            if (
                state.channel
                and user.voice
                and user.voice.channel
                and state.channel.id == user.voice.channel.id
            ):
                member = await guild.fetch_member(user_id)
                if member is not None:
                    mem.append(member)
        return mem

    @control_commands.command()
    @app_commands.describe(who="Who to mute:")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def mute(
        self,
        interaction: discord.Interaction,
        who: Optional[Literal["everyone", "everyone but me"]] = "everyone but me",
    ):
        """Mutes everyone in a voice channel"""

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this commannd."
            )

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel
        else:
            vc = None

        mem = await self.get_members(interaction.guild, interaction.user)

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

        self.client.log(
            LogLevel.DEBUG,
            f"Muted: {len(tasks)} g/{interaction.guild_id} c/{interaction.channel_id}",
        )

        return self.client.incr_counter("vc_mute")

    @control_commands.command()
    @app_commands.describe(who="Who to deafen:")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def deafen(
        self,
        interaction: discord.Interaction,
        who: Optional[Literal["everyone", "everyone but me"]] = "everyone but me",
    ):
        """Deafens everyone in a voice channel"""

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this commannd."
            )

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel
        else:
            vc = None

        mem = await self.get_members(interaction.guild, interaction.user)

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

        self.client.log(
            LogLevel.DEBUG,
            f"Deafened: {len(tasks)} g/{interaction.guild_id} c/{interaction.channel_id}",
        )

        return self.client.incr_counter("vc_deafen")

    @control_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def unmute(self, interaction: discord.Interaction):
        """Unmutes everyone in a voice channel"""

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this commannd."
            )

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel
        else:
            vc = None

        mem = await self.get_members(interaction.guild, interaction.user)

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

        self.client.log(
            LogLevel.DEBUG,
            f"Unmuted: {len(tasks)} g/{interaction.guild_id} c/{interaction.channel_id}",
        )

        return self.client.incr_counter("vc_unmute")

    @control_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def undeafen(self, interaction: discord.Interaction):
        """Undeafens everyone in a voice channel"""

        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this commannd."
            )

        if interaction.user.voice and interaction.user.voice.channel:
            vc = interaction.user.voice.channel
        else:
            vc = None

        mem = await self.get_members(interaction.guild, interaction.user)

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

        self.client.log(
            LogLevel.DEBUG,
            f"Undeafened: {len(tasks)} g/{interaction.guild_id} c/{interaction.channel_id}",
        )

        return self.client.incr_counter("vc_undeafen")


async def setup(client: VCRolesClient):
    await client.add_cog(VCControl(client))
