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
        data = self.client.jopen(f"Data/generator", str(member.guild.id))

        try:
            data[str(member.guild.id)]
        except:
            return

        if str(after.channel.id) == data[str(member.guild.id)]["gen_id"]:
            category = self.client.get_channel(int(data[str(member.guild.id)]["cat"]))

            channel = await member.guild.create_voice_channel(
                name=f"{member.display_name}",
                category=category,
                reason="Voice Channel Generator",
            )

            data[str(member.guild.id)]["open"].append(str(channel.id))

            await member.move_to(channel)

            self.client.jdump("Data/generator", data)

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        data = self.client.jopen(f"Data/generator", str(member.guild.id))

        try:
            data[str(member.guild.id)]
        except:
            return

        if str(before.channel.id) in data[str(member.guild.id)]["open"]:
            if len(before.channel.members) == 0:
                await before.channel.delete()

                data[str(member.guild.id)]["open"].remove(str(before.channel.id))

                self.client.jdump("Data/generator", data)
