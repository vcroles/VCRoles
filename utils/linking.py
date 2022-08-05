from typing import NamedTuple, Optional, Union

import discord

from utils.client import VCRolesClient
from utils.utils import handle_data_deletion


class LinkReturnData(NamedTuple):
    """Return data from linking"""

    status: bool
    message: str
    data: Optional[dict]


class LinkingUtils:
    def __init__(self, client: VCRolesClient):
        self.client = client

    async def link(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.StageChannel, discord.VoiceChannel, discord.CategoryChannel
        ],
        role: discord.Role,
        channel_type: Optional[str] = None,
        link_type: Optional[str] = "roles",
    ) -> LinkReturnData:
        """Use to link a channel and a role"""

        if channel_type is None:
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
            data[str(channel.id)] = {
                "roles": [],
                "suffix": "",
                "reverse_roles": [],
                "speaker_roles": [],
            }

        if str(role.id) not in data[str(channel.id)][link_type]:
            data[str(channel.id)][link_type].append(str(role.id))

            self.client.redis.update_linked(channel_type, interaction.guild_id, data)

            message = f"Linked {channel.mention} with role: `@{role.name}`"

            if channel_type == "permanent":
                message += "\nWhen a user leaves the channel, they will KEEP the role"

            member = interaction.guild.get_member(self.client.user.id)
            if member.top_role.position < role.position:
                message += f"\nPlease ensure my highest role is above `@{role.name}`"

            status = True
        else:
            message = f"The channel and role are already linked."
            status = False

        return LinkReturnData(status, message, data)

    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.StageChannel, discord.VoiceChannel, discord.CategoryChannel
        ],
        role: discord.Role,
        channel_type: Optional[str] = None,
        link_type: Optional[str] = "roles",
    ) -> LinkReturnData:
        """Use to unlink a channel and a role"""

        if not channel_type:
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
            return LinkReturnData(False, "The channel and role are not linked.")

        if str(role.id) in data[str(channel.id)][link_type]:
            try:
                data[str(channel.id)][link_type].remove(str(role.id))

                data = handle_data_deletion(data, str(channel.id))

                self.client.redis.update_linked(
                    channel_type, interaction.guild_id, data
                )

                message = f"Unlinked {channel.mention} and role: `@{role.name}`"
                status = True
            except:
                message = f"There was an error unlinking the channel and role."
                status = False

        else:
            message = f"The channel and role are not linked."
            status = False

        return LinkReturnData(status, message, data)

    async def suffix_add(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.StageChannel, discord.VoiceChannel, discord.CategoryChannel
        ],
        suffix: str,
        channel_type: Optional[str] = None,
    ) -> LinkReturnData:
        """Use to add a suffix to a channel"""

        if not channel_type:
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
            data[str(channel.id)] = {
                "roles": [],
                "suffix": "",
                "reverse_roles": [],
                "speaker_roles": [],
            }

        data[str(channel.id)]["suffix"] = suffix

        self.client.redis.update_linked(channel_type, interaction.guild_id, data)

        message = f"Set the suffix for {channel.mention} to `{suffix}`"

        return LinkReturnData(True, message, data)

    async def suffix_remove(
        self,
        interaction: discord.Interaction,
        channel: Union[
            discord.StageChannel, discord.VoiceChannel, discord.CategoryChannel
        ],
        channel_type: Optional[str] = None,
    ) -> LinkReturnData:
        """Use to remove a suffix from a channel"""

        if not channel_type:
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
            message = "The channel has no associated suffix."
            return LinkReturnData(False, message, data)

        data[str(channel.id)]["suffix"] = ""

        data = handle_data_deletion(data, str(channel.id))

        self.client.redis.update_linked(channel_type, interaction.guild_id, data)

        message = f"Removed the suffix for {channel.mention}"

        return LinkReturnData(True, message, data)
