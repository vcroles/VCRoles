from string import Template

import discord

from prisma.enums import VoiceGeneratorType, VoiceGeneratorOption

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
        if isinstance(user_channel, discord.StageChannel):
            return

        gen_data = await self.client.db.get_generator(member.guild.id, user_channel.id)

        if not gen_data:
            return

        count = len(gen_data.openChannels) if gen_data.openChannels else 0
        editable = VoiceGeneratorOption.EDITABLE in gen_data.defaultOptions

        if str(user_channel.id) != gen_data.generatorId:
            return

        if count >= gen_data.channelLimit:
            try:
                await member.move_to(None)
            except:
                pass
            finally:
                return

        if gen_data.type == VoiceGeneratorType.CLONED:
            channel = await user_channel.clone(
                name=f"[{user_channel.name}] #{count+1}",
                reason="Voice Channel Generator",
            )
        elif gen_data.type == VoiceGeneratorType.NUMBERED:
            channel = await member.guild.create_voice_channel(
                name=f"{gen_data.channelName} #{count+1}",
                category=user_channel.category,
                reason="Voice Channel Generator",
                overwrites={
                    member.guild.me: discord.PermissionOverwrite(
                        manage_channels=True, connect=True, view_channel=True
                    ),
                },
            )
        elif gen_data.type == VoiceGeneratorType.CUSTOM_NAME:
            channel = await member.guild.create_voice_channel(
                name=Template(
                    gen_data.channelName if gen_data.channelName else "$username"
                ).substitute(username=member.display_name, count=count + 1),
                category=user_channel.category,
                reason="Voice Channel Generator",
                overwrites={
                    member.guild.me: discord.PermissionOverwrite(
                        manage_channels=True, connect=True, view_channel=True
                    ),
                },
            )
        else:
            channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}",
                category=user_channel.category,
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
            pass

        await self.client.db.create_generated_channel(
            member.guild.id, user_channel.id, channel.id, member.id, editable
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
