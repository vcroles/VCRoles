import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner


class UnLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @app_commands.command()
    @app_commands.describe(channel_id="Enter the channel ID")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def forceunlink(
        self,
        interaction: discord.Interaction,
        channel_id: str,
    ):
        """Use to remove any channel/category from all links (Using ID)"""

        channel_id = channel_id.strip()
        data = self.client.redis.get_linked("voice", interaction.guild_id)
        if channel_id in data:
            del data[channel_id]
            self.client.redis.update_linked("voice", interaction.guild_id, data)

        data = self.client.redis.get_linked("permanent", interaction.guild_id)
        if channel_id in data:
            del data[channel_id]
            self.client.redis.update_linked("permanent", interaction.guild_id, data)

        data = self.client.redis.get_linked("all", interaction.guild_id)
        if channel_id in data["except"]:
            data["except"].remove(channel_id)
            self.client.redis.update_linked("all", interaction.guild_id, data)

        data = self.client.redis.get_linked("stage", interaction.guild_id)
        if channel_id in data:
            del data[channel_id]
            self.client.redis.update_linked("stage", interaction.guild_id, data)

        data = self.client.redis.get_linked("category", interaction.guild_id)
        if channel_id in data:
            del data[channel_id]
            self.client.redis.update_linked("category", interaction.guild_id, data)

        await interaction.response.send_message(
            f"Any found links to {channel_id} have been removed."
        )

        return self.client.incr_counter("forceunlink")


async def setup(client: MyClient):
    await client.add_cog(UnLink(client))
