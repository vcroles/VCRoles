import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient


class Ping(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        """Used to view the ping of the bot"""

        await interaction.response.send_message(
            f"Pong! {round(self.client.latency*1000,1)} ms"
        )

        return self.client.incr_counter("ping")


async def setup(client: MyClient):
    await client.add_cog(Ping(client))
