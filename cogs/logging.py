from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class Logging(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @app_commands.command(description="Used to enable disable logging, in a channel.")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(
        enabled="Enter 'true' to enable or 'false' to disable",
        channel="Logging channel:",
    )
    async def logging(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        channel: Optional[discord.TextChannel] = None,
    ):
        if enabled == True and not channel:
            channel = interaction.channel
        if enabled == True and channel:
            try:
                data = self.client.redis.get_guild_data(interaction.guild_id)

                data["logging"] = str(channel.id)

                self.client.redis.update_guild_data(interaction.guild_id, data)

                await interaction.response.send_message(
                    f"Successfully enabled logging in {channel.mention}"
                )
            except:
                await interaction.response.send_message(f"Unable to enable logging")
        elif enabled == False:
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


async def setup(client: MyClient):
    await client.add_cog(Logging(client))
