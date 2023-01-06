import discord
from discord import app_commands
from discord.ext import commands
from prisma.enums import LinkType

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from utils.linking import LinkingUtils
from utils.types import LogLevel, RoleCategory


class StageSpeaker(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.linking = LinkingUtils(client)

    stage_commands = app_commands.Group(
        name="stage", description="Stage channel commands"
    )
    speaker_commands = app_commands.Group(
        name="speaker", description="Stage speaker commands", parent=stage_commands
    )

    @speaker_commands.command()
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def link(
        self,
        interaction: discord.Interaction,
        channel: discord.StageChannel,
        role: discord.Role,
    ):
        """Link a stage channel speaker to a role"""

        data = await self.linking.link(
            interaction, channel, role, LinkType.STAGE, RoleCategory.STAGE_SPEAKER
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Speaker linked c/{channel.id} g/{interaction.guild_id} r/{role.id}",
        )

        return self.client.incr_counter("speaker_link")

    @speaker_commands.command()
    @app_commands.describe(
        channel="Select a channel to unlink", role="Select a role to unlink"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: discord.StageChannel,
        role: discord.Role,
    ):
        """Unlink a stage channel speaker from a role"""

        data = await self.linking.unlink(
            interaction, channel, role, LinkType.STAGE, RoleCategory.STAGE_SPEAKER
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Speaker unlinked c/{channel.id} g/{interaction.guild_id} r/{role.id}",
        )

        return self.client.incr_counter("speaker_unlink")


async def setup(client: VCRolesClient):
    await client.add_cog(StageSpeaker(client))
