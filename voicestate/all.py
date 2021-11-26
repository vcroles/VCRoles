import discord


class all:
    def __init__(self, client: discord.AutoShardedBot):
        self.client = client

    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        if data["all"]["roles"]:
            if str(after.channel.id) in data["all"]["except"]:
                return None
            roles = []
            for i in data["all"]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Joined voice channel")
                    roles.append(role)
                except:
                    pass
            return roles
        return None

    async def leave(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        if data["all"]["roles"]:
            if str(before.channel.id) in data["all"]["except"]:
                return None
            roles = []
            for i in data["all"]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    roles.append(role)
                except:
                    pass
            return roles
        return None
