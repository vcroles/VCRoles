import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient


class Advanced(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def advanced(
        self,
        interaction: discord.Interaction,
    ):
        """
        REMOVED. Command for advanced users. Allows you to add/remove/edit a large number of links at once.
        """
        await interaction.response.send_message("This command has been removed.")

    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def export(self, interaction: discord.Interaction):
        """
        REMOVED. Command for advanced users. Allows you to export all links to a file.
        """
        await interaction.response.send_message("This command has been removed.")


async def setup(client: VCRolesClient):
    await client.add_cog(Advanced(client))
