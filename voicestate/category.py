import discord


class Category:
    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        try:
            after.channel.category
        except:
            return None
        if str(after.channel.category.id) in data:
            roles = []
            for i in data[str(after.channel.category.id)]:
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
        try:
            before.channel.category
        except:
            return None
        if str(before.channel.category.id) in data:
            roles = []
            for i in data[str(before.channel.category.id)]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    roles.append(role)
                except:
                    pass
            return roles
        return None
