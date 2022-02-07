import json
import discord
from bot import MyClient


class generator:
    def __init__(self, client: MyClient):
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

            channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                reason="Voice Channel Generator",
            )
            await member.move_to(channel)
            data["open"] = json.loads(data["open"])
            data["open"].append(str(channel.id))

            self.client.redis.update_gen_open(member.guild.id, data["open"])

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        data = self.client.redis.get_generator(member.guild.id)
        data["open"] = self.client.redis.str_to_list(data["open"])

        if str(before.channel.id) in data["open"]:
            if len(before.channel.members) == 0:
                await before.channel.delete()

                data["open"].remove(str(before.channel.id))

                self.client.redis.update_gen_open(member.guild.id, data["open"])
