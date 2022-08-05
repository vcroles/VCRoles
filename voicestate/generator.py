import json

import discord

from utils.client import VCRolesClient


class Generator:
    def __init__(self, client: VCRolesClient):
        self.client = client

    async def join(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        data = self.client.redis.get_generator(member.guild.id)

        if str(after.channel.id) == data["gen_id"]:
            category = self.client.get_channel(int(data["cat"]))

            overwrites = {
                member.guild.me: discord.PermissionOverwrite(
                    manage_channels=True, connect=True, view_channel=True
                ),
            }

            channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                reason="Voice Channel Generator",
                overwrites=overwrites,
            )
            await member.move_to(channel)
            data["open"].append(str(channel.id))

            self.client.redis.update_gen_open(member.guild.id, data["open"])

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        data = self.client.redis.get_generator(member.guild.id)

        if str(before.channel.id) in data["open"]:
            if not before.channel.members:
                await before.channel.delete()

                data["open"].remove(str(before.channel.id))

                self.client.redis.update_gen_open(member.guild.id, data["open"])
