import discord

from utils import add_suffix, remove_suffix


class All:
    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        await add_suffix(member, data["suffix"])
        if data["roles"]:
            if str(after.channel.id) in data["except"]:
                return None

            roles = []
            for i in data["roles"]:
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
        await remove_suffix(member, data["suffix"])
        if data["roles"]:
            if str(before.channel.id) in data["except"]:
                return None

            roles = []
            for i in data["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    roles.append(role)
                except:
                    pass
            return roles
        return None
