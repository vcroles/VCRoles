from prisma import Prisma
from prisma.models import Guild, Link
from prisma.enums import LinkType
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

    async def update_guild_data(self, guild_id: DiscordID, data: Guild) -> None:
        await self.db.guild.update(
            where={"id": str(guild_id)},
            data={
                "ttsEnabled": data.ttsEnabled,
                "ttsRole": data.ttsRole,
                "ttsLeave": data.ttsLeave,
                "logging": data.logging,
            },
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
                {"guildId": str(guild_id), "id": str(channel_id)}
            )
        return data

    async def update_channel_linked(
        self,
        channel_id: DiscordID,
        data: Link,
        link_type: LinkType = LinkType.REGULAR,
    ) -> None:
        await self.db.link.update(
            where={"id_type": {"id": str(channel_id), "type": link_type}},
            data={
                "linkedRoles": data.linkedRoles,
                "reverseLinkedRoles": data.reverseLinkedRoles,
                "suffix": data.suffix,
                "speakerRoles": data.speakerRoles,
                "excludeChannels": data.excludeChannels,
            },
        )
