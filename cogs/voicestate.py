import discord
from discord.ext import commands

from bot import MyClient
from utils import add_suffix, remove_suffix
from voicestate.all import All
from voicestate.generator import Generator
from voicestate.logging import Logging


class VoiceState(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client
        self.all = All()
        self.generator = Generator(client)
        self.logging = Logging(client)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot == True:
            return

        # Joining
        if not before.channel and after.channel:
            roles_changed = await self.join(member, before, after)

            if roles_changed:
                (
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                    perm_changed,
                ) = roles_changed

                await self.logging.log_join(
                    after,
                    member,
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                    perm_changed,
                )

        # Leaving
        elif before.channel and not after.channel:
            roles_changed = await self.leave(member, before, after)

            if roles_changed:
                (
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                ) = roles_changed

                await self.logging.log_leave(
                    before,
                    member,
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                )

        # Changing
        elif before.channel != after.channel:
            leave_roles_changed = await self.leave(member, before, after)
            join_roles_changed = await self.join(member, before, after)

            if leave_roles_changed and join_roles_changed:
                await self.logging.log_change(
                    before,
                    after,
                    member,
                    leave_roles_changed,
                    join_roles_changed,
                )

    async def join(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        voice_changed = (
            stage_changed
        ) = category_changed = all_changed = perm_changed = {
            "added": [],
            "removed": [],
        }

        try:
            after.channel.type
        except:
            return

        if isinstance(after.channel, discord.VoiceChannel):
            try:
                voice_changed = await self.handle_join(
                    self.client.redis.get_linked("voice", member.guild.id),
                    member,
                    after.channel.id,
                    linktype="voice",
                )
            except:
                pass

        elif isinstance(after.channel, discord.StageChannel):
            try:
                stage_changed = await self.handle_join(
                    self.client.redis.get_linked("stage", member.guild.id),
                    member,
                    after.channel.id,
                    linktype="stage",
                )
            except:
                pass

        try:
            category_changed = await self.handle_join(
                self.client.redis.get_linked("category", member.guild.id),
                member,
                after.channel.category.id,
                linktype="category",
            )
        except:
            pass

        try:
            all_changed = await self.all.join(
                self.client.redis.get_linked("all", member.guild.id),
                member,
                before,
                after,
            )
        except:
            pass

        try:
            perm_changed = await self.handle_join(
                self.client.redis.get_linked("permanent", member.guild.id),
                member,
                after.channel.id,
                linktype="permanent",
            )
        except:
            pass

        try:
            await self.generator.join(member, before, after)
        except:
            pass

        return (
            voice_changed,
            stage_changed,
            category_changed,
            all_changed,
            perm_changed,
        )

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        voice_changed = stage_changed = category_changed = all_changed = {
            "added": [],
            "removed": [],
        }

        try:
            before.channel.type
        except:
            return

        try:
            all_changed = await self.all.leave(
                self.client.redis.get_linked("all", member.guild.id),
                member,
                before,
                after,
            )
        except:
            pass

        try:
            category_changed = await self.handle_leave(
                self.client.redis.get_linked("category", member.guild.id),
                member,
                before.channel.category.id,
                linktype="category",
            )
        except:
            pass

        if isinstance(before.channel, discord.StageChannel):
            try:
                stage_changed = await self.handle_leave(
                    self.client.redis.get_linked("stage", member.guild.id),
                    member,
                    before.channel.id,
                    linktype="stage",
                )
            except:
                pass

        if isinstance(before.channel, discord.VoiceChannel):
            try:
                voice_changed = await self.handle_leave(
                    self.client.redis.get_linked("voice", member.guild.id),
                    member,
                    before.channel.id,
                    linktype="voice",
                )
            except:
                pass

        try:
            await self.generator.leave(member, before, after)
        except:
            pass

        return (voice_changed, stage_changed, category_changed, all_changed)

    async def handle_join(
        self,
        data: dict[str, dict[str, list | str, str]],
        member: discord.Member,
        id: str | int,
        linktype: str,
    ) -> dict[str, list]:
        if isinstance(id, int):
            id = str(id)
        if id in data:
            await add_suffix(member, data[id]["suffix"])
            added = []
            for i in data[id]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Joined voice channel")
                    added.append(role)
                except:
                    pass
            removed = []
            for i in data[id]["reverse_roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Joined voice channel")
                    removed.append(role)
                except:
                    pass
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}

    async def handle_leave(
        self,
        data: dict[str, dict[str, list | str, str]],
        member: discord.Member,
        id: str | int,
        linktype: str,
    ) -> dict[str, list]:
        if isinstance(id, int):
            id = str(id)
        if id in data:
            await remove_suffix(
                member, (data[id]["suffix"] if linktype != "all" else data["suffix"])
            )
            added = []
            for i in (
                data[id]["reverse_roles"]
                if linktype != "all"
                else data["reverse_roles"]
            ):
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Left voice channel")
                    added.append(role)
                except:
                    pass
            removed = []
            for i in data[id]["roles"] if linktype != "all" else data["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    removed.append(role)
                except:
                    pass
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}


def setup(client: MyClient):
    client.add_cog(VoiceState(client))
