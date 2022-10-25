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

        channel_data = await self.client.db.get_generated_channel(user_channel.id)
        # add new user to text channel permissions
        if channel_data and channel_data.textChannelId:
            user_text_channel = self.client.get_channel(int(channel_data.textChannelId))
            if not user_text_channel or not isinstance(
                user_text_channel, discord.TextChannel
            ):
                pass
            else:
                text_overwrites = user_text_channel.overwrites
                try:
                    text_overwrites[member].view_channel = True
                    text_overwrites[member].send_messages = True
                except KeyError:
                    text_overwrites[member] = discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    )
                await user_text_channel.edit(overwrites=text_overwrites)

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

        if gen_data.defaultRole:
            default_role = member.guild.get_role(int(gen_data.defaultRole))
            if not default_role:
                default_role = member.guild.default_role
        else:
            default_role = member.guild.default_role

        overwrites: dict[
            discord.Role | discord.Member, discord.PermissionOverwrite
        ] = {}

        if VoiceGeneratorOption.LOCK in gen_data.defaultOptions:
            try:
                overwrites[default_role].connect = False
            except KeyError:
                overwrites[default_role] = discord.PermissionOverwrite(connect=False)
        if VoiceGeneratorOption.HIDE in gen_data.defaultOptions:
            try:
                overwrites[default_role].view_channel = False
            except KeyError:
                overwrites[default_role] = discord.PermissionOverwrite(
                    view_channel=False
                )

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
                    **overwrites,
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
                    **overwrites,
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
                    **overwrites,
                },
            )

        if VoiceGeneratorOption.TEXT in gen_data.defaultOptions:
            text_channel = await member.guild.create_text_channel(
                name=f"{member.display_name}-text",
                category=user_channel.category,
                reason="Voice Channel Generator",
                overwrites={
                    member.guild.me: discord.PermissionOverwrite(
                        manage_channels=True, send_messages=True, view_channel=True
                    ),
                    member: discord.PermissionOverwrite(
                        view_channel=True, send_messages=True
                    ),
                    default_role: discord.PermissionOverwrite(
                        view_channel=False, send_messages=False
                    ),
                },
            )
            await text_channel.send(
                f"{member.mention} this is your generated text channel."
            )
        else:
            text_channel = None

        try:
            await member.move_to(channel)
        except:
            pass

        await self.client.db.create_generated_channel(
            member.guild.id,
            user_channel.id,
            channel.id,
            member.id,
            editable,
            text_channel_id=str(text_channel.id)
            if text_channel is not None
            else text_channel,
        )

    async def leave(
        self,
        member: discord.Member,
        user_channel: JoinableChannel,
    ):
        data = await self.client.db.get_generated_channel(user_channel.id)

        if not data:
            return

        if not user_channel.members:
            await user_channel.delete()
            if data.textChannelId:
                text_channel = self.client.get_channel(int(data.textChannelId))
                if text_channel and isinstance(text_channel, discord.TextChannel):
                    await text_channel.delete()

            await self.client.db.delete_generated_channel(user_channel.id)
        else:
            if data.textChannelId:
                text_channel = self.client.get_channel(int(data.textChannelId))
                if text_channel and isinstance(text_channel, discord.TextChannel):
                    overwrites = text_channel.overwrites
                    try:
                        overwrites[member].send_messages = False
                        overwrites[member].view_channel = False
                    except KeyError:
                        overwrites[member] = discord.PermissionOverwrite(
                            send_messages=False, view_channel=False
                        )
                    await text_channel.edit(overwrites=overwrites)
