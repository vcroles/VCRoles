from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient


class Logging(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    @app_commands.command()
    @app_commands.describe(
        enabled="Enter 'true' to enable or 'false' to disable",
        channel="Logging channel:",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def logging(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        channel: Optional[discord.TextChannel] = None,
    ):
        """Used to enable or disable logging in a channel."""

        if enabled and not channel:
            channel = interaction.channel
        if enabled and channel:
            try:
                data = self.client.redis.get_guild_data(interaction.guild_id)

                data["logging"] = str(channel.id)

                self.client.redis.update_guild_data(interaction.guild_id, data)

                await interaction.response.send_message(
                    f"Successfully enabled logging in {channel.mention}"
                )
            except:
                await interaction.response.send_message(f"Unable to enable logging")
        elif not enabled:
            try:
                data = self.client.redis.get_guild_data(interaction.guild_id)

                data["logging"] = "None"

                self.client.redis.update_guild_data(interaction.guild_id, data)

                await interaction.response.send_message(
                    f"Successfully disabled logging"
                )
            except:
                await interaction.response.send_message("Unable to disable logging")

        return self.client.incr_counter("logging")


async def setup(client: VCRolesClient):
    await client.add_cog(Logging(client))
