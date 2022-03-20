import discord

from utils import add_suffix, remove_suffix


class Category:
    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> dict[str, list]:
        try:
            after.channel.category
        except:
            return {"added": [], "removed": []}
        if str(after.channel.category.id) in data:
            await add_suffix(member, data[str(after.channel.category.id)]["suffix"])
            added = []
            for i in data[str(after.channel.category.id)]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Joined voice channel")
                    added.append(role)
                except:
                    pass
            removed = []
            for i in data[str(after.channel.category.id)]["reverse_roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Joined voice channel")
                    removed.append(role)
                except:
                    pass
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}

    async def leave(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> dict[str, list]:
        try:
            before.channel.category
        except:
            return {"added": [], "removed": []}
        if str(before.channel.category.id) in data:
            await remove_suffix(member, data[str(before.channel.category.id)]["suffix"])
            removed = []
            for i in data[str(before.channel.category.id)]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    removed.append(role)
                except:
                    pass
            added = []
            for i in data[str(before.channel.category.id)]["reverse_roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Left voice channel")
                    added.append(role)
                except:
                    pass
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}
