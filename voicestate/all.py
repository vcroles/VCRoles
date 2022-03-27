import discord

from utils import add_suffix, remove_suffix


class All:
    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> dict[str, list]:
        await add_suffix(member, data["suffix"])
        if str(after.channel.id) in data["except"]:
            return {"added": [], "removed": []}
        added = []
        for i in data["roles"]:
            try:
                role = member.guild.get_role(int(i))
                await member.add_roles(role, reason="Joined voice channel")
                added.append(role)
            except:
                pass
        removed = []
        for i in data["reverse_roles"]:
            try:
                role = member.guild.get_role(int(i))
                await member.remove_roles(role, reason="Joined voice channel")
                removed.append(role)
            except:
                pass
        return {"added": added, "removed": removed}

    async def leave(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> dict[str, list]:
        await remove_suffix(member, data["suffix"])
        if str(before.channel.id) in data["except"]:
            return None

        removed = []
        for i in data["roles"]:
            try:
                role = member.guild.get_role(int(i))
                await member.remove_roles(role, reason="Left voice channel")
                removed.append(role)
            except:
                pass
        added = []
        for i in data["reverse_roles"]:
            try:
                role = member.guild.get_role(int(i))
                await member.add_roles(role, reason="Left voice channel")
                added.append(role)
            except:
                pass
        return {"added": added, "removed": removed}
