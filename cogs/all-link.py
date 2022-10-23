from typing import Union

import discord
from discord import app_commands
from discord.ext import commands
from prisma.enums import LinkType

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient


class AllLink(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    all_commands = app_commands.Group(
        name="all", description="Rules to apply to all channels"
    )
    exclude_commands = app_commands.Group(
        name="exclude",
        description="Channels to exclude from rules",
        parent=all_commands,
    )
    suffix_commands = app_commands.Group(
        name="suffix",
        description="Suffix to add to the end of usernames",
        parent=all_commands,
    )
    reverse_commands = app_commands.Group(
        name="reverse", description="Reverse roles", parent=all_commands
    )

    @all_commands.command()
    @app_commands.describe(role="Select a role to link")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def link(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        """Use to link all channels with a role"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )

        if str(role.id) not in data.linkedRoles:
            data.linkedRoles.append(str(role.id))

            await self.client.db.update_channel_linked(
                interaction.guild.id, LinkType.ALL, linked_roles=data.linkedRoles
            )

            await interaction.response.send_message(
                f"Linked all channels with role: `@{role.name}`"
            )

            if not self.client.user:
                return

            member = interaction.guild.get_member(self.client.user.id)

            if not member:
                return

            if member.top_role.position < role.position:
                await interaction.followup.send(
                    f"Please ensure my highest role is above `@{role.name}`"
                )
        else:
            await interaction.response.send_message(
                f"The channel and role are already linked."
            )

        return self.client.incr_counter("all_link")

    @all_commands.command()
    @app_commands.describe(role="Select a role to unlink")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def unlink(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        """Use to unlink all channels from a role"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )

        if str(role.id) in data.linkedRoles:
            data.linkedRoles.remove(str(role.id))

            await self.client.db.update_channel_linked(
                interaction.guild.id, LinkType.ALL, linked_roles=data.linkedRoles
            )

            await interaction.response.send_message(
                f"Unlinked all channels from role: `@{role.name}`"
            )
        else:
            await interaction.response.send_message(
                f"The channel and role are not linked."
            )

        return self.client.incr_counter("all_unlink")

    @exclude_commands.command(name="add")
    @app_commands.describe(channel="Select a channel to exclude")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_exclude(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
    ):
        """Use to create an exception to the all link command"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )

        try:
            if str(channel.id) not in data.excludeChannels:
                data.excludeChannels.append(str(channel.id))

                await self.client.db.update_channel_linked(
                    interaction.guild.id,
                    LinkType.ALL,
                    exclude_channels=data.excludeChannels,
                )

                await interaction.response.send_message(
                    f"Added exception: `{channel.name}`"
                )
            else:
                await interaction.response.send_message(
                    f"The channel is already an exception."
                )
        except:
            await interaction.response.send_message(f"Unable to add exception")

        return self.client.incr_counter("all_add_exception")

    @exclude_commands.command(name="remove")
    @app_commands.describe(channel="Select a channel to un-exclude")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_exclude(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
    ):
        """Use to remove an exception to the all link command"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )

        if str(channel.id) in data.excludeChannels:
            data.excludeChannels.remove(str(channel.id))

            await self.client.db.update_channel_linked(
                interaction.guild.id,
                LinkType.ALL,
                exclude_channels=data.excludeChannels,
            )

            await interaction.response.send_message(
                f"Removed {channel.mention} as an exception to alllink"
            )
        else:
            await interaction.response.send_message(
                f"Please select a valid exception channel"
            )

        return self.client.incr_counter("all_remove_exception")

    @suffix_commands.command(name="add")
    @app_commands.describe(
        suffix="The suffix to add to your username when joining any channel"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_suffix(
        self,
        interaction: discord.Interaction,
        suffix: str,
    ):
        """Use to add a suffix to users"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        await self.client.db.update_channel_linked(
            interaction.guild.id, LinkType.ALL, suffix=suffix
        )

        await interaction.response.send_message(
            f"When members join any channel, their username will be appended with `{suffix}`"
        )

        return self.client.incr_counter("all_add_suffix")

    @suffix_commands.command(name="remove")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_suffix(self, interaction: discord.Interaction):
        """Use to remove a username suffix rule"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        await self.client.db.update_channel_linked(
            interaction.guild.id, LinkType.ALL, suffix="None"
        )

        await interaction.response.send_message("Removed the username suffix rule")

        return self.client.incr_counter("all_remove_suffix")

    @reverse_commands.command(name="link")
    @app_commands.describe(role="Select a role to reverse link")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_link(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        """Use to add a reverse link"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )

        if str(role.id) not in data.reverseLinkedRoles:
            data.reverseLinkedRoles.append(str(role.id))

            await self.client.db.update_channel_linked(
                interaction.guild.id,
                LinkType.ALL,
                reverse_linked_roles=data.reverseLinkedRoles,
            )

            await interaction.response.send_message(
                f"Added reverse link: `@{role.name}`"
            )
        else:
            await interaction.response.send_message(
                f"The role is already a reverse link."
            )

        return self.client.incr_counter("all_reverse_link")

    @reverse_commands.command(name="unlink")
    @app_commands.describe(role="Select a role to un-reverse link")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def reverse_unlink(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ):
        """Use to remove a reverse link"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        data = await self.client.db.get_channel_linked(
            interaction.guild.id, interaction.guild.id, LinkType.ALL
        )

        if str(role.id) in data.reverseLinkedRoles:
            try:
                data.reverseLinkedRoles.remove(str(role.id))

                await self.client.db.update_channel_linked(
                    interaction.guild.id,
                    LinkType.ALL,
                    reverse_linked_roles=data.reverseLinkedRoles,
                )

                await interaction.response.send_message(
                    f"Removed reverse link: `@{role.name}`"
                )
            except:
                pass
        else:
            await interaction.response.send_message(f"The role is not a reverse link.")

        return self.client.incr_counter("all_reverse_unlink")


async def setup(client: VCRolesClient):
    await client.add_cog(AllLink(client))
