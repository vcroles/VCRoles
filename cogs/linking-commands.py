import json
from typing import Any, Tuple

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


def check_criteria(criteria: dict[Any, Any], path: str) -> Tuple[bool, str]:
    print(criteria, path)

    if len(criteria) != 1:
        return False, f"Invalid criteria structure at path: {path}"

    if "and" in criteria or "or" in criteria:
        for idx, c in enumerate(criteria["and"]):
            result = check_criteria(c, f"{path}['and'][{idx}]")
            if result[0] is False:
                return result
    if "not" in criteria:
        result = check_criteria(criteria["not"], f"{path}['not']")
        if result[0] is False:
            return result

    key, value = next(iter(criteria.items()))

    if key not in ["isUser", "hasRole", "hasPermission"]:
        return False, f"Invalid criteria at path: {path}"
    else:
        if not isinstance(value, str):
            return False, f"Invalid criteria value at path: {path}"
        else:
            return True, ""


def check_json(user_input: str) -> Tuple[dict[Any, Any], bool, str]:
    try:
        user_dict = json.loads(user_input)

        if not isinstance(user_dict, dict):
            return {}, False, "Invalid JSON format. Must be a dictionary"

        res = check_criteria(user_dict, "")  # type: ignore

        return user_dict, res[0], res[1]  # type: ignore
    except json.JSONDecodeError as e:
        return {}, False, f"Invalid JSON format. {str(e)}"


class Linking(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.linking_utils = LinkingUtils(client)

    suffix_commands = app_commands.Group(
        name="suffix", description="Suffix to add to the end of usernames"
    )
    reverse_commands = app_commands.Group(name="reverse", description="Reverse roles")

    @app_commands.command()
    @app_commands.describe(channel="Select a channel to link", role="Select a role to link")
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
    @app_commands.describe(channel="Select a channel to unlink", role="Select a role to unlink")
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
    @app_commands.describe(channel="Select a channel to link", role="Select a role to link")
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
    @app_commands.describe(channel="Select a channel to link", role="Select a role to link")
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

    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_link_criteria(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        link_type: LinkType,
        criteria: str,
    ):
        """Use to set the link criteria for a channel"""

        if not interaction.guild_id or not interaction.guild:
            return await interaction.response.send_message(
                "This command must be run in a guild.", ephemeral=True
            )

        # Check if the criteria is valid JSON
        criteria_dict = check_json(criteria)

        if criteria_dict[1] is False:
            return await interaction.response.send_message(
                f"Invalid criteria: {criteria_dict[2]}", ephemeral=True
            )

        await self.client.db.update_channel_linked(
            channel.id, interaction.guild_id, link_type, link_criteria=criteria_dict[0]
        )

        await interaction.response.send_message(
            f"Set link criteria to `{criteria}` for {channel.mention}"
        )

        self.client.log(
            LogLevel.DEBUG,
            f"Set link criteria c/{channel.id} g/{interaction.guild_id} t/{link_type} c/{criteria}",
        )

    # add a command which removes the link criteria
    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_link_criteria(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        link_type: LinkType,
    ):
        """Use to remove the link criteria for a channel"""

        if not interaction.guild_id or not interaction.guild:
            return await interaction.response.send_message(
                "This command must be run in a guild.", ephemeral=True
            )

        await self.client.db.update_channel_linked(
            channel.id, interaction.guild_id, link_type, link_criteria={}
        )

        await interaction.response.send_message(f"Removed link criteria for {channel.mention}")

        self.client.log(
            LogLevel.DEBUG,
            f"Removed link criteria c/{channel.id} g/{interaction.guild_id} t/{link_type}",
        )


async def setup(client: VCRolesClient):
    await client.add_cog(Linking(client))
