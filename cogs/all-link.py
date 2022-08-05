from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from utils.checks import check_any, command_available, is_owner


class AllLink(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    all_commands = app_commands.Group(
        name="all", description="Rules to apply to all channels"
    )
    exception_commands = app_commands.Group(
        name="exception",
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

        data = self.client.redis.get_linked("all", interaction.guild_id)

        if str(role.id) not in data["roles"]:
            data["roles"].append(str(role.id))

            self.client.redis.update_linked("all", interaction.guild_id, data)

            await interaction.response.send_message(
                f"Linked all channels with role: `@{role.name}`"
            )

            member = interaction.guild.get_member(self.client.user.id)
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

        data = self.client.redis.get_linked("all", interaction.guild_id)

        if str(role.id) in data["roles"]:
            data["roles"].remove(str(role.id))

            self.client.redis.update_linked("all", interaction.guild_id, data)

            await interaction.response.send_message(
                f"Unlinked all channels from role: `@{role.name}`"
            )
        else:
            await interaction.response.send_message(
                f"The channel and role are not linked."
            )

        return self.client.incr_counter("all_unlink")

    @exception_commands.command()
    @app_commands.describe(channel="Select a channel to exclude")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def add(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
    ):
        """Use to create an exception to the all link command"""

        data = self.client.redis.get_linked("all", interaction.guild_id)

        try:
            if str(channel.id) not in data["except"]:
                data["except"].append(str(channel.id))

                self.client.redis.update_linked("all", interaction.guild_id, data)

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

    @exception_commands.command()
    @app_commands.describe(channel="Select a channel to un-exclude")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(
        self,
        interaction: discord.Interaction,
        channel: Union[discord.VoiceChannel, discord.StageChannel],
    ):
        """Use to remove an exception to the all link command"""

        data = self.client.redis.get_linked("all", interaction.guild_id)

        if str(channel.id) in data["except"]:
            data["except"].remove(str(channel.id))

            self.client.redis.update_linked("all", interaction.guild_id, data)

            await interaction.response.send_message(
                f"Removed {channel.mention} as an exception to alllink"
            )
        else:
            await interaction.response.send_message(
                f"Please select a valid exception channel"
            )

        return self.client.incr_counter("all_remove_exception")

    @suffix_commands.command()
    @app_commands.describe(
        suffix="The suffix to add to your username when joining any channel"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def add(
        self,
        interaction: discord.Interaction,
        suffix: str,
    ):
        """Use to add a suffix to users"""

        data = self.client.redis.get_linked("all", interaction.guild_id)
        data["suffix"] = suffix
        self.client.redis.update_linked("all", interaction.guild_id, data)

        await interaction.response.send_message(
            f"When members join any channel, their username will be appended with `{suffix}`"
        )

        return self.client.incr_counter("all_add_suffix")

    @suffix_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction):
        """Use to remove a username suffix rule"""

        data = self.client.redis.get_linked("all", interaction.guild_id)
        data["suffix"] = ""
        self.client.redis.update_linked("all", interaction.guild_id, data)

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

        data = self.client.redis.get_linked("all", interaction.guild_id)

        if str(role.id) not in data["reverse_roles"]:
            data["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked("all", interaction.guild_id, data)

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

        data = self.client.redis.get_linked("all", interaction.guild_id)

        if str(role.id) in data["reverse_roles"]:
            try:
                data["reverse_roles"].remove(str(role.id))

                self.client.redis.update_linked("all", interaction.guild_id, data)

                await interaction.response.send_message(
                    f"Removed reverse link: `@{role.name}`"
                )
            except:
                pass
        else:
            await interaction.response.send_message(f"The role is not a reverse link.")

        return self.client.incr_counter("all_reverse_unlink")


async def setup(client: MyClient):
    await client.add_cog(AllLink(client))
