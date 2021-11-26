import discord


class category:
    def __init__(self, client: discord.AutoShardedBot):
        self.client = client

    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        if str(after.channel.category.id) in data["category"]:
            roles = []
            for i in data["category"][str(after.channel.category.id)]:
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
        if str(before.channel.category.id) in data["category"]:
            roles = []
            for i in data["category"][str(before.channel.category.id)]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    roles.append(role)
                except:
                    pass
            return roles
        return None

    async def change(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        removed_roles = await self.leave(data, member, before, after)
        added_roles = await self.join(data, member, before, after)
        return [removed_roles, added_roles]
