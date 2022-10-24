import discord
from discord import app_commands
from discord.ext import commands

from utils import GeneratorUtils
from utils.client import VCRolesClient


class GenInterface(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.utils = GeneratorUtils(client.db)

    interface_commands = app_commands.Group(
        name="interface", description="Interface commands"
    )

    @interface_commands.command(name="lock")
    async def lock_interface(self, interaction: discord.Interaction):
        """Lock your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.lock(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_lock")

    @interface_commands.command(
        name="unlock",
    )
    async def unlock_interface(self, interaction: discord.Interaction):
        """Unlock your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.unlock(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_unlock")

    @interface_commands.command(
        name="hide",
    )
    async def hide_interface(self, interaction: discord.Interaction):
        """Hide your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.hide(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_hide")

    @interface_commands.command(name="show")
    async def unhide_interface(self, interaction: discord.Interaction):
        """Show your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.unhide(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_unhide")

    @interface_commands.command(
        name="increase",
    )
    async def increase_limit_interface(self, interaction: discord.Interaction):
        """Increase your generated voice channel user limit"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.increase_limit(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_increase")

    @interface_commands.command(name="decrease")
    async def decrease_limit_interface(self, interaction: discord.Interaction):
        """Decrease your generated voice channel user limit"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.decrease_limit(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_decrease")

    @interface_commands.command(name="rename")
    @app_commands.describe(name="The new name.")
    async def rename_channel(self, interaction: discord.Interaction, name: str):
        """Rename your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.rename(interaction.user, name)
        await interaction.response.send_message(message, ephemeral=True)

        return self.client.incr_counter("interface_rename")


async def setup(client: VCRolesClient):
    await client.add_cog(GenInterface(client))
