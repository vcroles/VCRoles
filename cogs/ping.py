import discord
from discord import app_commands
from discord.ext import commands

from utils.client import VCRolesClient


class Ping(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        """Used to view the ping of the bot"""

        await interaction.response.send_message(
            f"Pong! {round(self.client.latency * 1000, 1)} ms"
        )


async def setup(client: VCRolesClient):
    await client.add_cog(Ping(client))
