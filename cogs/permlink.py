from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner
from utils import handle_data_deletion


class PermLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

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

        data = self.client.redis.get_linked("permanent", interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["roles"]:
            data[str(channel.id)]["roles"].append(str(role.id))

            self.client.redis.update_linked("permanent", interaction.guild_id, data)

            await interaction.response.send_message(
                f"Linked {channel.mention} with role: `@{role.name}`\nWhen a user leaves the channel, they will KEEP the role"
            )

            member = interaction.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await interaction.channel.send(
                    f"Please ensure my highest role is above `@{role.name}`"
                )
        else:
            await interaction.response.send_message(
                f"The channel and role are already linked."
            )

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

        data = self.client.redis.get_linked("permanent", interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            await interaction.response.send_message(
                f"The channel and role are not linked."
            )
            return

        if str(role.id) in data[str(channel.id)]["roles"]:
            try:
                data[str(channel.id)]["roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("permanent", interaction.guild_id, data)

                await interaction.response.send_message(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass

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

        data = self.client.redis.get_linked("permanent", interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked("permanent", interaction.guild_id, data)

        await interaction.response.send_message(
            f"Added suffix rule of `{suffix}` for {channel.mention}"
        )

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

        data = self.client.redis.get_linked("permanent", interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            await interaction.response.send_message(
                f"The channel has no associated rules."
            )
            return

        data[str(channel.id)]["suffix"] = ""

        data = handle_data_deletion(data, str(channel.id))

        self.client.redis.update_linked("permanent", interaction.guild_id, data)

        await interaction.response.send_message(
            f"Removed suffix rule for {channel.mention}"
        )

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

        data = self.client.redis.get_linked("permanent", interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["reverse_roles"]:
            data[str(channel.id)]["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("permanent", interaction.guild_id, data)

            await interaction.response.send_message(
                f"Linked {channel.mention} with role: `@{role.name}`"
            )

            member = interaction.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                await interaction.channel.send(
                    f"Please ensure my highest role is above `@{role.name}`"
                )
        else:
            await interaction.response.send_message(
                f"The channel and role are already linked."
            )

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

        data = self.client.redis.get_linked("permanent", interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            return await interaction.response.send_message(
                f"The channel and role are not linked."
            )

        if str(role.id) in data[str(channel.id)]["reverse_roles"]:
            try:
                data[str(channel.id)]["reverse_roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked("permanent", interaction.guild_id, data)

                await interaction.response.send_message(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                pass

        return self.client.incr_counter("perm_reverse_unlink")


async def setup(client: MyClient):
    await client.add_cog(PermLink(client))
