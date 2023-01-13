import discord
from discord import app_commands
from discord.ext import commands
from prisma.enums import LinkType

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from utils.linking import LinkingUtils
from utils.types import LinkableChannel, LogLevel, RoleCategory


def infer_link_type(channel: LinkableChannel) -> LinkType:
    if isinstance(channel, discord.VoiceChannel):
        return LinkType.REGULAR
    elif isinstance(channel, discord.StageChannel):
        return LinkType.STAGE
    else:
        return LinkType.CATEGORY


class Linking(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.linking_utils = LinkingUtils(client)

    suffix_commands = app_commands.Group(
        name="suffix", description="Suffix to add to the end of usernames"
    )
    reverse_commands = app_commands.Group(name="reverse", description="Reverse roles")

    @app_commands.command()
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def link(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        role: discord.Role,
    ):
        """Use to link a channel with a role"""

        data = await self.linking_utils.link(
            interaction, channel, role, infer_link_type(channel), RoleCategory.REGULAR
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Linked c/{channel.id} g/{interaction.guild_id} r/{role.id}",
        )

    @app_commands.command()
    @app_commands.describe(
        channel="Select a channel to unlink", role="Select a role to unlink"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        role: discord.Role,
    ):
        """Use to unlink a channel from a role"""

        data = await self.linking_utils.unlink(
            interaction, channel, role, infer_link_type(channel), RoleCategory.REGULAR
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Unlinked c/{channel.id} g/{interaction.guild_id} r/{role.id}",
        )

    @suffix_commands.command()
    @app_commands.describe(
        channel="Select a channel to link",
        suffix="Add a suffix to the end of usernames",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def add(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        suffix: str,
    ):
        """Use to set a suffix for a channel"""

        data = await self.linking_utils.suffix_add(
            interaction, channel, suffix, infer_link_type(channel)
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Added suffix c/{channel.id} g/{interaction.guild_id} s/{suffix}",
        )

    @suffix_commands.command()
    @app_commands.describe(channel="Select a channel to link")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
    ):
        """Use to remove a suffix for a channel"""

        data = await self.linking_utils.suffix_remove(
            interaction, channel, infer_link_type(channel)
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Removed suffix c/{channel.id} g/{interaction.guild_id}",
        )

    @reverse_commands.command(name="link")
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_link(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        role: discord.Role,
    ):
        """Use to add a reverse role link"""

        data = await self.linking_utils.link(
            interaction, channel, role, infer_link_type(channel), RoleCategory.REVERSE
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Reverse linked c/{channel.id} g/{interaction.guild_id} r/{role.id}",
        )

    @reverse_commands.command(name="unlink")
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        role: discord.Role,
    ):
        """Use to remove a reverse role link"""

        data = await self.linking_utils.unlink(
            interaction, channel, role, infer_link_type(channel), RoleCategory.REVERSE
        )

        await interaction.response.send_message(data.message)

        self.client.log(
            LogLevel.DEBUG,
            f"Reverse unlinked c/{channel.id} g/{interaction.guild_id} r/{role.id}",
        )


async def setup(client: VCRolesClient):
    await client.add_cog(Linking(client))
