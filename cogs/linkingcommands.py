from typing import Union

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from utils import Permissions, handle_data_deletion


class Linking(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    suffix_commands = app_commands.Group(
        name="suffix", description="Suffix to add to the end of usernames"
    )
    reverse_commands = app_commands.Group(name="reverse", description="Reverse roles")

    @app_commands.command(description="Use to link channels with roles")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    async def link(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):

        if isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "stage"

        data = self.client.redis.get_linked(channel_type, interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["roles"]:
            data[str(channel.id)]["roles"].append(str(role.id))

            self.client.redis.update_linked(channel_type, interaction.guild_id, data)

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

        return self.client.incr_counter("link")

    @app_commands.command(description="Use to unlink a channel from a role")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Select a channel to unlink", role="Select a role to unlink"
    )
    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):

        if isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "stage"

        data = self.client.redis.get_linked(channel_type, interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            return await interaction.response.send_message(
                f"The channel and role are not linked."
            )

        if str(role.id) in data[str(channel.id)]["roles"]:
            try:
                data[str(channel.id)]["roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked(
                    channel_type, interaction.guild_id, data
                )

                await interaction.response.send_message(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                return await interaction.response.send_message(
                    f"There was an error unlinking the channel and role."
                )

        else:
            await interaction.response.send_message(
                f"The channel and role are not linked."
            )

        return self.client.incr_counter("unlink")

    @suffix_commands.command(description="Use to set a suffix for a channel")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Select a channel to link",
        suffix="Add a suffix to the end of usernames",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        suffix: str,
    ):

        if isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "stage"

        data = self.client.redis.get_linked(channel_type, interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked(channel_type, interaction.guild_id, data)

        await interaction.response.send_message(
            f"Set the suffix for {channel.mention} to `{suffix}`"
        )

        return self.client.incr_counter("add_suffix")

    @suffix_commands.command(description="Use to remove a suffix for a channel")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(channel="Select a channel to link")
    async def remove(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
    ):

        if isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "stage"

        data = self.client.redis.get_linked(channel_type, interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            return await interaction.response.send_message(
                f"The channel has no associated rules."
            )

        data[str(channel.id)]["suffix"] = ""

        data = handle_data_deletion(data, str(channel.id))

        self.client.redis.update_linked(channel_type, interaction.guild_id, data)

        await interaction.response.send_message(
            f"Removed the suffix for {channel.mention}"
        )

        return self.client.incr_counter("remove_suffix")

    @reverse_commands.command(description="Use to add a reverse role link", name="link")
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    async def reverse_link(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):

        if isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "stage"

        data = self.client.redis.get_linked(channel_type, interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            data[str(channel.id)] = {"roles": [], "suffix": "", "reverse_roles": []}

        if str(role.id) not in data[str(channel.id)]["reverse_roles"]:
            data[str(channel.id)]["reverse_roles"].append(str(role.id))

            self.client.redis.update_linked(channel_type, interaction.guild_id, data)

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

        return self.client.incr_counter("reverse_link")

    @reverse_commands.command(
        description="Use to remove a reverse role link", name="unlink"
    )
    @Permissions.has_permissions(administrator=True)
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    async def reverse_unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.CategoryChannel, discord.VoiceChannel, discord.StageChannel
        ],
        role: discord.Role,
    ):

        if isinstance(channel, discord.CategoryChannel):
            channel_type = "category"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "stage"

        data = self.client.redis.get_linked(channel_type, interaction.guild_id)

        try:
            data[str(channel.id)]
        except:
            return await interaction.response.send_message(
                f"The channel has no associated rules."
            )

        if str(role.id) in data[str(channel.id)]["reverse_roles"]:
            try:
                data[str(channel.id)]["reverse_roles"].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked(
                    channel_type, interaction.guild_id, data
                )

                await interaction.response.send_message(
                    f"Unlinked {channel.mention} and role: `@{role.name}`"
                )
            except:
                return await interaction.response.send_message(
                    f"There was an error unlinking the channel and role."
                )

        else:
            await interaction.response.send_message(
                f"The channel and role are not linked."
            )

        return self.client.incr_counter("reverse_unlink")


async def setup(client: MyClient):
    await client.add_cog(Linking(client))
