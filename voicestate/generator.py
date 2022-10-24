import discord

from utils.client import VCRolesClient
from utils.types import JoinableChannel


class Generator:
    def __init__(self, client: VCRolesClient):
        self.client = client

    async def join(
        self,
        member: discord.Member,
        user_channel: JoinableChannel,
    ) -> None:
        gen_data = await self.client.db.get_generator(member.guild.id, user_channel.id)

        if not gen_data:
            return

        if str(user_channel.id) == gen_data.generatorId:
            category = self.client.get_channel(int(gen_data.categoryId))

            if not isinstance(category, discord.CategoryChannel):
                return

            channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                reason="Voice Channel Generator",
                overwrites={
                    member.guild.me: discord.PermissionOverwrite(
                        manage_channels=True, connect=True, view_channel=True
                    ),
                },
            )

            try:
                await member.move_to(channel)
            except:
                return

            await self.client.db.create_generated_channel(
                member.guild.id, user_channel.id, channel.id, member.id
            )

    async def leave(
        self,
        member: discord.Member,
        user_channel: JoinableChannel,
    ):
        data = await self.client.db.get_generated_channel(user_channel.id)

        if data:
            if not user_channel.members:
                await user_channel.delete()

                await self.client.db.delete_generated_channel(user_channel.id)
