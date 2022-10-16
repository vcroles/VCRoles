import discord

from prisma.enums import LinkType

from utils.client import VCRolesClient
from utils.types import LinkableChannel, LinkReturnData, RoleCategory


class LinkingUtils:
    def __init__(self, client: VCRolesClient):
        self.client = client

    async def link(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        role: discord.Role,
        link_type: LinkType,
        role_category: RoleCategory,
    ) -> LinkReturnData:
        if not interaction.guild_id or not interaction.guild:
            return LinkReturnData(False, "Guild ID not present", None)

        data = await self.client.db.get_channel_linked(
            channel.id, interaction.guild_id, link_type
        )

        if role_category == RoleCategory.REGULAR:
            linked_roles = data.linkedRoles
        elif role_category == RoleCategory.REVERSE:
            linked_roles = data.reverseLinkedRoles
        elif role_category == RoleCategory.STAGE_SPEAKER:
            linked_roles = data.speakerRoles

        if str(role.id) not in linked_roles:
            linked_roles.append(str(role.id))

            if role_category == RoleCategory.REGULAR:
                await self.client.db.update_channel_linked(
                    channel.id, link_type, linked_roles=linked_roles
                )
            elif role_category == RoleCategory.REVERSE:
                await self.client.db.update_channel_linked(
                    channel.id, link_type, reverse_linked_roles=linked_roles
                )
            elif role_category == RoleCategory.STAGE_SPEAKER:
                await self.client.db.update_channel_linked(
                    channel.id, link_type, speaker_roles=linked_roles
                )

            message = f"Linked {channel.mention} with role `@{role.name}`"

            if link_type == LinkType.PERMANENT:
                message += "\nWhen a user leaves the channel, they will KEEP the role"

            if self.client.user:
                member = interaction.guild.get_member(self.client.user.id)
                if member and member.top_role.position < role.position:
                    message += (
                        f"\nPlease ensure my highest role is above `@{role.name}`"
                    )

            status = True
        else:
            message = f"The channel and role are already linked."
            status = False

        return LinkReturnData(status, message, data)

    async def unlink(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        role: discord.Role,
        link_type: LinkType,
        role_category: RoleCategory,
    ) -> LinkReturnData:
        if not interaction.guild_id or not interaction.guild:
            return LinkReturnData(False, "Guild ID not present", None)

        data = await self.client.db.get_channel_linked(
            channel.id, interaction.guild_id, link_type
        )

        if role_category == RoleCategory.REGULAR:
            linked_roles = data.linkedRoles
        elif role_category == RoleCategory.REVERSE:
            linked_roles = data.reverseLinkedRoles
        elif role_category == RoleCategory.STAGE_SPEAKER:
            linked_roles = data.speakerRoles

        if str(role.id) in linked_roles:
            linked_roles.remove(str(role.id))

            if role_category == RoleCategory.REGULAR:
                await self.client.db.update_channel_linked(
                    channel.id, link_type, linked_roles=linked_roles
                )
            elif role_category == RoleCategory.REVERSE:
                await self.client.db.update_channel_linked(
                    channel.id, link_type, reverse_linked_roles=linked_roles
                )
            elif role_category == RoleCategory.STAGE_SPEAKER:
                await self.client.db.update_channel_linked(
                    channel.id, link_type, speaker_roles=linked_roles
                )

            message = f"Unlinked {channel.mention} and role: `@{role.name}`"
            status = True
        else:
            message = "The channel and role are not linked."
            status = False

        return LinkReturnData(status, message, data)

    async def suffix_add(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        suffix: str,
        link_type: LinkType,
    ) -> LinkReturnData:
        if not interaction.guild_id or not interaction.guild:
            return LinkReturnData(False, "Guild ID not present", None)

        data = await self.client.db.get_channel_linked(
            channel.id, interaction.guild_id, link_type
        )

        data.suffix = suffix

        await self.client.db.update_channel_linked(channel.id, link_type, suffix=suffix)

        message = f"Set the suffix for {channel.mention} to `{suffix}`"

        return LinkReturnData(True, message, data)

    async def suffix_remove(
        self,
        interaction: discord.Interaction,
        channel: LinkableChannel,
        link_type: LinkType,
    ) -> LinkReturnData:
        if not interaction.guild_id or not interaction.guild:
            return LinkReturnData(False, "Guild ID not present", None)

        await self.client.db.update_channel_linked(channel.id, link_type, suffix="")

        message = f"Removed the suffix for {channel.mention}"

        return LinkReturnData(True, message, None)
