import discord

from utils import add_suffix, remove_suffix


class Voice:
    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list:
        if str(after.channel.id) in data:
            await add_suffix(member, data[str(after.channel.id)]["suffix"])
            roles = []
            for i in data[str(after.channel.id)]["roles"]:
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
        if str(before.channel.id) in data:
            await remove_suffix(member, data[str(before.channel.id)]["suffix"])
            roles = []
            for i in data[str(before.channel.id)]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    roles.append(role)
                except:
                    pass
            return roles
        return None
