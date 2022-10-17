from typing import List, Optional

from prisma import Prisma
from prisma.enums import LinkType
from prisma.models import Guild, Link, VoiceGenerator
from prisma.types import GuildUpdateInput, LinkUpdateInput, VoiceGeneratorUpdateInput

from utils.types import DiscordID


class DatabaseUtils:
    """Tools for interacting with the database"""

    def __init__(self) -> None:
        self.db = Prisma()

    async def connect(self) -> None:
        await self.db.connect()

    async def disconnect(self) -> None:
        await self.db.disconnect()

    async def guild_remove(self, guild_id: DiscordID) -> None:
        await self.db.guild.delete(where={"id": str(guild_id)})

    async def get_guild_data(self, guild_id: DiscordID) -> Guild:
        data = await self.db.guild.find_unique(where={"id": str(guild_id)})
        if not data:
            data = await self.db.guild.create({"id": str(guild_id)})
        return data

    async def update_guild_data(
        self,
        guild_id: DiscordID,
        tts_enabled: Optional[bool] = None,
        tts_role: Optional[str] = None,
        tts_leave: Optional[bool] = None,
        logging: Optional[str] = None,
    ) -> None:
        data: GuildUpdateInput = {}

        if tts_enabled is not None:
            data["ttsEnabled"] = tts_enabled

        if tts_role is not None:
            data["ttsRole"] = tts_role

        if tts_leave is not None:
            data["ttsLeave"] = tts_leave

        if logging is not None:
            data["logging"] = logging

        await self.db.guild.update(where={"id": str(guild_id)}, data=data)

    async def get_channel_linked(
        self,
        channel_id: DiscordID,
        guild_id: DiscordID,
        link_type: LinkType = LinkType.REGULAR,
    ) -> Link:
        data = await self.db.link.find_first(
            where={"AND": [{"id": str(channel_id)}, {"type": link_type}]}
        )
        if not data:
            await self.get_guild_data(guild_id)
            data = await self.db.link.create(
                {"guildId": str(guild_id), "id": str(channel_id), "type": link_type}
            )
        return data

    async def update_channel_linked(
        self,
        channel_id: DiscordID,
        link_type: LinkType = LinkType.REGULAR,
        linked_roles: Optional[List[str]] = None,
        reverse_linked_roles: Optional[List[str]] = None,
        speaker_roles: Optional[List[str]] = None,
        exclude_channels: Optional[List[str]] = None,
        suffix: Optional[str] = None,
    ) -> None:
        data: LinkUpdateInput = {}

        if linked_roles is not None:
            data["linkedRoles"] = linked_roles

        if reverse_linked_roles is not None:
            data["reverseLinkedRoles"] = reverse_linked_roles

        if speaker_roles is not None:
            data["speakerRoles"] = speaker_roles

        if exclude_channels is not None:
            data["excludeChannels"] = exclude_channels

        if suffix is not None:
            data["suffix"] = suffix

        await self.db.link.update(
            where={"id_type": {"id": str(channel_id), "type": link_type}}, data=data
        )

    async def get_all_linked(self, guild_id: DiscordID) -> List[Link]:
        guild = await self.db.guild.find_unique(
            where={"id": str(guild_id)}, include={"links": True}
        )
        if not guild:
            guild = await self.db.guild.create(
                {"id": str(guild_id)}, include={"links": True}
            )

        return guild.links or []

    async def get_generator(self, guild_id: DiscordID) -> VoiceGenerator:
        data = await self.db.voicegenerator.find_unique(
            where={"guildId": str(guild_id)}
        )
        if not data:
            await self.get_guild_data(guild_id)
            data = await self.db.voicegenerator.create({"guildId": str(guild_id)})
        return data

    async def update_generator(
        self,
        guild_id: DiscordID,
        category_id: Optional[str] = None,
        generator_id: Optional[str] = None,
        interface_channel: Optional[str] = None,
        interface_message: Optional[str] = None,
        open_channels: Optional[List[str]] = None,
    ) -> None:
        data: VoiceGeneratorUpdateInput = {}

        if category_id is not None:
            data["categoryId"] = category_id

        if generator_id is not None:
            data["generatorId"] = generator_id

        if interface_channel is not None:
            data["interfaceChannel"] = interface_channel

        if interface_message is not None:
            data["interfaceMessage"] = interface_message

        if open_channels is not None:
            data["openChannels"] = open_channels

        await self.db.voicegenerator.update(where={"guildId": str(guild_id)}, data=data)
