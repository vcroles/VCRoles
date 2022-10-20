import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from prisma.enums import LinkType


class UnLink(commands.Cog):
    def __init__(self, client: VCRolesClient):
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

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a guild to use this command."
            )

        channel_id = channel_id.strip()

        await self.client.db.db.link.delete_many(
            where={"id": channel_id, "guildId": str(interaction.guild.id)}
        )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )
        if channel_id in data.excludeChannels:
            data.excludeChannels.remove(channel_id)
            await self.client.db.update_channel_linked(
                interaction.guild.id,
                LinkType.ALL,
                exclude_channels=data.excludeChannels,
            )

        await interaction.response.send_message(
            f"Any found links to {channel_id} have been removed."
        )

        return self.client.incr_counter("forceunlink")


async def setup(client: VCRolesClient):
    await client.add_cog(UnLink(client))
