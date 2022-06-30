from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner
from utils.linking import LinkingUtils


class PermLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client
        self.linking = LinkingUtils(client)

    perm_commands = app_commands.Group(
        name="permanent", description="Rules to apply to permanent channels"
    )
    suffix_commands = app_commands.Group(
        name="suffix",
        description="Suffix to add to the end of usernames",
        parent=perm_commands,
    )
    reverse_commands = app_commands.Group(
        name="reverse", description="Reverse roles", parent=perm_commands
    )

    @perm_commands.command()
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def link(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel
        ],
        role: discord.Role,
    ):
        """Use to link a channel and a role (after leaving channel, user will keep role)"""

        data = await self.linking.link(
            interaction, channel, role, channel_type="permanent"
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("perm_link")

    @perm_commands.command()
    @app_commands.describe(
        channel="Select a channel to unlink", role="Select a role to unlink"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel
        ],
        role: discord.Role,
    ):
        """Use to unlink a "permanent" channel from a role"""

        data = await self.linking.unlink(
            interaction, channel, role, channel_type="permanent"
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("perm_unlink")

    @suffix_commands.command()
    @app_commands.describe(
        channel="Select a channel to set a suffix for",
        suffix="Suffix to add to the end of usernames",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def add(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel
        ],
        suffix: str,
    ):
        """Use to set a suffix to add to the end of usernames"""

        data = await self.linking.suffix_add(
            interaction, channel, suffix, channel_type="permanent"
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("perm_suffix_add")

    @suffix_commands.command()
    @app_commands.describe(channel="Select a channel to remove a suffix rule from")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel
        ],
    ):
        """Use to remove a suffix rule from a channel"""

        data = await self.linking.suffix_remove(
            interaction, channel, channel_type="permanent"
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("perm_suffix_remove")

    @reverse_commands.command(
        name="link",
    )
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_link(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel
        ],
        role: discord.Role,
    ):
        """Use to reverse link a channel and a role"""

        data = await self.linking.link(
            interaction,
            channel,
            role,
            link_type="reverse_roles",
            channel_type="permanent",
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("perm_reverse_link")

    @reverse_commands.command(
        name="unlink",
    )
    @app_commands.describe(
        channel="Select a channel to unlink", role="Select a role to unlink"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel
        ],
        role: discord.Role,
    ):
        """Use to unlink a reverse role"""

        data = await self.linking.unlink(
            interaction,
            channel,
            role,
            link_type="reverse_roles",
            channel_type="permanent",
        )

        await interaction.response.send_message(data.message)

        return self.client.incr_counter("perm_reverse_unlink")


async def setup(client: MyClient):
    await client.add_cog(PermLink(client))
