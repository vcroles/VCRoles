from typing import List, Optional

from prisma import Prisma
from prisma.enums import LinkType, VoiceGeneratorOption, VoiceGeneratorType
from prisma.models import GeneratedChannel, Guild, Link, VoiceGenerator
from prisma.types import (
    GeneratedChannelUpdateInput,
    GuildUpdateInput,
    LinkUpdateInput,
    VoiceGeneratorUpdateInput,
)

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
        await self.db.link.delete_many(where={"guildId": str(guild_id)})
        await self.db.voicegenerator.delete_many(where={"guildId": str(guild_id)})
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

        if tts_role == "None":
            data["ttsRole"] = None

        if tts_leave is not None:
            data["ttsLeave"] = tts_leave

        if logging is not None:
            data["logging"] = logging

        if logging == "None":
            data["logging"] = None

        res = await self.db.guild.update(where={"id": str(guild_id)}, data=data)
        if not res:
            await self.db.guild.create(
                {
                    "id": str(guild_id),
                    "ttsEnabled": tts_enabled if tts_enabled else False,
                    "ttsRole": data.get("ttsRole"),
                    "ttsLeave": tts_leave if tts_leave else True,
                    "logging": logging if logging != "None" else None,
                }
            )

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

        if suffix == "None":
            data["suffix"] = None

        res = await self.db.link.update(
            where={"id_type": {"id": str(channel_id), "type": link_type}}, data=data
        )
        if not res:
            await self.db.link.create(
                {
                    "id": str(channel_id),
                    "type": link_type,
                    "linkedRoles": linked_roles if linked_roles else [],
                    "reverseLinkedRoles": reverse_linked_roles
                    if reverse_linked_roles
                    else [],
                    "speakerRoles": speaker_roles if speaker_roles else [],
                    "excludeChannels": exclude_channels if exclude_channels else [],
                    "suffix": suffix if suffix != "None" else None,
                }
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

    async def get_generators(self, guild_id: DiscordID) -> list[VoiceGenerator]:
        data = await self.db.voicegenerator.find_many(
            where={"guildId": str(guild_id)}, include={"openChannels": True}
        )
        if not data:
            return []
        return data

    async def get_generator(
        self, guild_id: DiscordID, generator_id: DiscordID
    ) -> Optional[VoiceGenerator]:
        data = await self.db.voicegenerator.find_unique(
            where={
                "guildId_generatorId": {
                    "generatorId": str(generator_id),
                    "guildId": str(guild_id),
                }
            },
            include={"openChannels": True},
        )
        return data

    async def update_generator(
        self,
        guild_id: DiscordID,
        generator_id: DiscordID,
        category_id: DiscordID,
        interface_channel: Optional[str] = None,
        interface_message: Optional[str] = None,
        gen_type: Optional[VoiceGeneratorType] = None,
        default_options: Optional[list[VoiceGeneratorOption]] = None,
        default_user_limit: Optional[int] = None,
        channel_limit: Optional[int] = None,
        default_role_id: Optional[str] = None,
    ) -> None:
        data: VoiceGeneratorUpdateInput = {}

        if interface_channel is not None:
            data["interfaceChannel"] = interface_channel

        if interface_message is not None:
            data["interfaceMessage"] = interface_message

        if gen_type is not None:
            data["type"] = gen_type

        if default_options is not None:
            data["defaultOptions"] = default_options

        if default_user_limit is not None:
            data["defaultUserLimit"] = default_user_limit

        if channel_limit is not None:
            data["channelLimit"] = channel_limit

        if default_role_id is not None:
            data["defaultRole"] = default_role_id

        res = await self.db.voicegenerator.update(
            where={
                "guildId_generatorId": {
                    "guildId": str(guild_id),
                    "generatorId": str(generator_id),
                }
            },
            data=data,
        )
        if not res:
            await self.db.voicegenerator.create(
                {
                    "guildId": str(guild_id),
                    "generatorId": str(generator_id),
                    "categoryId": str(category_id),
                    "interfaceChannel": data.get("interfaceChannel"),
                    "interfaceMessage": data.get("interfaceMessage"),
                }
            )

    async def get_generated_channel(
        self, channel_id: DiscordID
    ) -> Optional[GeneratedChannel]:
        data = await self.db.generatedchannel.find_unique(
            where={"channelId": str(channel_id)}, include={"VoiceGenerator": True}
        )
        return data

    async def delete_generated_channel(self, channel_id: DiscordID) -> None:
        await self.db.generatedchannel.delete(where={"channelId": str(channel_id)})

    async def update_generated_channel(
        self,
        channel_id: DiscordID,
        owner_id: Optional[DiscordID] = None,
        text_channel_id: Optional[str] = None,
        user_editable: Optional[bool] = None,
    ) -> None:
        data: GeneratedChannelUpdateInput = {}

        if owner_id is not None:
            data["ownerId"] = str(owner_id)

        if text_channel_id is not None:
            data["textChannelId"] = text_channel_id

        if text_channel_id == "None":
            data["textChannelId"] = None

        if user_editable is not None:
            data["userEditable"] = user_editable

        await self.db.generatedchannel.update(
            where={"channelId": str(channel_id)}, data=data
        )

    async def create_generated_channel(
        self,
        guild_id: DiscordID,
        generator_id: DiscordID,
        channel_id: DiscordID,
        owner_id: DiscordID,
        user_editable: bool = True,
    ) -> GeneratedChannel:
        data = await self.db.generatedchannel.create(
            data={
                "VoiceGenerator": {
                    "connect": {
                        "guildId_generatorId": {
                            "guildId": str(guild_id),
                            "generatorId": str(generator_id),
                        }
                    }
                },
                "channelId": str(channel_id),
                "ownerId": str(owner_id),
                "userEditable": user_editable,
            }
        )
        return data

    async def delete_generator(
        self, guild_id: DiscordID, generator_id: DiscordID
    ) -> None:
        await self.db.voicegenerator.delete(
            where={
                "guildId_generatorId": {
                    "guildId": str(guild_id),
                    "generatorId": str(generator_id),
                }
            }
        )

    async def get_all_linked_channel(
        self,
        guild_id: DiscordID,
        channel_id: DiscordID,
        category_id: Optional[DiscordID] = None,
    ) -> List[Link]:

        if category_id:
            s = [str(channel_id), str(category_id), str(guild_id)]
        else:
            s = [str(channel_id), str(guild_id)]

        guild = await self.db.guild.find_unique(
            where={"id": str(guild_id)},
            include={"links": {"where": {"OR": [{"id": i} for i in s]}}},
        )
        if not guild:
            guild = await self.db.guild.create(
                {"id": str(guild_id)}, include={"links": True}
            )

        return guild.links or []
