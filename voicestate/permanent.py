import discord
from bot import MyClient


class perm:
    def __init__(self, client: MyClient):
        self.client = client

    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        if str(after.channel.id) in data["permanent"]:
            roles = []
            for i in data["permanent"][str(after.channel.id)]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role)
                    roles.append(role)
                except:
                    pass
            return roles
        return None
