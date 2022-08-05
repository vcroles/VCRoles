from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from utils.linking import LinkingUtils


class Linking(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.linking = LinkingUtils(client)

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
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):
        """Use to link a channel with a role"""

        data = await self.linking.link(interaction, channel, role)

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("link")

    @app_commands.command()
    @app_commands.describe(
        channel="Select a channel to unlink", role="Select a role to unlink"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):
        """Use to unlink a channel from a role"""

        data = await self.linking.unlink(interaction, channel, role)

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("unlink")

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
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        suffix: str,
    ):
        """Use to set a suffix for a channel"""

        data = await self.linking.suffix_add(interaction, channel, suffix)

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("add_suffix")

    @suffix_commands.command()
    @app_commands.describe(channel="Select a channel to link")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
    ):
        """Use to remove a suffix for a channel"""

        data = await self.linking.suffix_remove(interaction, channel)

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("remove_suffix")

    @reverse_commands.command(name="link")
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_link(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):
        """Use to add a reverse role link"""

        data = await self.linking.link(
            interaction, channel, role, link_type="reverse_roles"
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("reverse_link")

    @reverse_commands.command(name="unlink")
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):
        """Use to remove a reverse role link"""

        data = await self.linking.unlink(
            interaction, channel, role, link_type="reverse_roles"
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("reverse_unlink")


async def setup(client: VCRolesClient):
    await client.add_cog(Linking(client))
