import discord

from utils import add_suffix


class Permanent:
    async def join(
        self,
        data,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> dict[str, list]:
        if str(after.channel.id) in data:
            await add_suffix(member, data[str(after.channel.id)]["suffix"])
            added = []
            for i in data[str(after.channel.id)]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Joined voice channel")
                    added.append(role)
                except:
                    pass
            removed = []
            for i in data[str(after.channel.id)]["reverse_roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Joined voice channel")
                    removed.append(role)
                except:
                    pass
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}
