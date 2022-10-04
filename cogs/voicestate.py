import asyncio

import discord
from discord.ext import commands

from utils.client import VCRolesClient
from utils.utils import ReturnData, add_suffix, remove_suffix
from voicestate.all import All
from voicestate.generator import Generator
from voicestate.logging import Logging


class VoiceState(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.all = All(client)
        self.generator = Generator(client)
        self.logging = Logging(client)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        # Joining
        if not before.channel and after.channel:
            roles_changed = await self.join(member, before, after)

            if roles_changed:
                await self.logging.log_join(
                    after,
                    member,
                    roles_changed,
                )

        # Leaving
        elif before.channel and not after.channel:
            roles_changed = await self.leave(member, before, after)

            if roles_changed:
                await self.logging.log_leave(
                    before,
                    member,
                    roles_changed,
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

        if (
            isinstance(before.channel, discord.StageChannel)
            and isinstance(after.channel, discord.StageChannel)
            and before.channel.id == after.channel.id
        ):
            # Become Speaker
            if before.suppress and not after.suppress:
                data = self.client.redis.get_linked("stage", member.guild.id)

                if str(before.channel.id) not in data:
                    return
                if "speaker_roles" not in data[str(before.channel.id)]:
                    data[str(before.channel.id)]["speaker_roles"] = []

                for i in data[str(before.channel.id)]["speaker_roles"]:
                    try:
                        role = member.guild.get_role(int(i))
                        await member.add_roles(role, reason="Became Speaker")
                    except:
                        pass
            # Stop Speaker
            elif not before.suppress and after.suppress:
                data = self.client.redis.get_linked("stage", member.guild.id)

                if str(before.channel.id) not in data:
                    return
                if "speaker_roles" not in data[str(before.channel.id)]:
                    data[str(before.channel.id)]["speaker_roles"] = []

                for i in data[str(before.channel.id)]["speaker_roles"]:
                    try:
                        role = member.guild.get_role(int(i))
                        await member.remove_roles(role, reason="Stopped Speaker")
                    except:
                        pass

    async def join(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> ReturnData:
        try:
            after.channel.type
        except:
            return

        if isinstance(after.channel, discord.VoiceChannel):
            voice_changed_task = self.client.loop.create_task(
                self.handle_join(
                    self.client.redis.get_linked("voice", member.guild.id),
                    member,
                    after.channel.id,
                )
            )
        else:
            voice_changed_task = self.client.loop.create_task(self.return_data())

        if isinstance(after.channel, discord.StageChannel):
            stage_changed_task = self.client.loop.create_task(
                self.handle_join(
                    self.client.redis.get_linked("stage", member.guild.id),
                    member,
                    after.channel.id,
                )
            )
        else:
            stage_changed_task = self.client.loop.create_task(self.return_data())

        if after.channel.category:
            category_changed_task = self.client.loop.create_task(
                self.handle_join(
                    self.client.redis.get_linked("category", member.guild.id),
                    member,
                    after.channel.category.id,
                )
            )
        else:
            category_changed_task = self.client.loop.create_task(self.return_data())

        all_changed_task = self.client.loop.create_task(
            self.all.join(
                self.client.redis.get_linked("all", member.guild.id),
                member,
                before,
                after,
            )
        )

        perm_changed_task = self.client.loop.create_task(
            self.handle_join(
                self.client.redis.get_linked("permanent", member.guild.id),
                member,
                after.channel.id,
            )
        )

        if after.channel.category:
            perm_cat_changed_task = self.client.loop.create_task(
                self.handle_join(
                    self.client.redis.get_linked("permanent", member.guild.id),
                    member,
                    after.channel.category.id,
                )
            )
        else:
            perm_cat_changed_task = self.client.loop.create_task(self.return_data())

        generator_task = self.client.loop.create_task(
            self.generator.join(member, before, after)
        )

        (
            voice_changed,
            stage_changed,
            category_changed,
            all_changed,
            perm_changed,
            perm_cat_changed,
            gen,
        ) = await asyncio.gather(
            voice_changed_task,
            stage_changed_task,
            category_changed_task,
            all_changed_task,
            perm_changed_task,
            perm_cat_changed_task,
            generator_task,
        )

        perm_changed["added"].extend(perm_cat_changed["added"])
        perm_changed["removed"].extend(perm_cat_changed["removed"])

        return ReturnData(
            voice_changed,
            stage_changed,
            category_changed,
            all_changed,
            perm_changed,
            gen,
        )

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> ReturnData:
        try:
            before.channel.type
        except:
            return

        all_changed_task = self.client.loop.create_task(
            self.all.leave(
                self.client.redis.get_linked("all", member.guild.id),
                member,
                before,
                after,
            )
        )

        if before.channel.category:
            category_changed_task = self.client.loop.create_task(
                self.handle_leave(
                    self.client.redis.get_linked("category", member.guild.id),
                    member,
                    before.channel.category.id,
                )
            )
        else:
            category_changed_task = self.client.loop.create_task(self.return_data())

        if isinstance(before.channel, discord.StageChannel):
            stage_changed_task = self.client.loop.create_task(
                self.handle_leave(
                    self.client.redis.get_linked("stage", member.guild.id),
                    member,
                    before.channel.id,
                )
            )
        else:
            stage_changed_task = self.client.loop.create_task(self.return_data())

        if isinstance(before.channel, discord.VoiceChannel):
            voice_changed_task = self.client.loop.create_task(
                self.handle_leave(
                    self.client.redis.get_linked("voice", member.guild.id),
                    member,
                    before.channel.id,
                )
            )
        else:
            voice_changed_task = self.client.loop.create_task(self.return_data())

        generator_task = self.client.loop.create_task(
            self.generator.leave(member, before, after)
        )

        (
            all_changed,
            category_changed,
            stage_changed,
            voice_changed,
            gen,
        ) = await asyncio.gather(
            all_changed_task,
            category_changed_task,
            stage_changed_task,
            voice_changed_task,
            generator_task,
        )

        return ReturnData(
            voice_changed,
            stage_changed,
            category_changed,
            all_changed,
            gen_data=gen,
        )

    async def handle_join(
        self,
        data: dict,
        member: discord.Member,
        id,
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
            self.client.incr_role_counter("added", len(added))
            self.client.incr_role_counter("removed", len(removed))
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}

    async def handle_leave(
        self,
        data: dict[str, dict],
        member: discord.Member,
        id,
    ) -> dict[str, list]:
        if isinstance(id, int):
            id = str(id)
        if id in data:
            await remove_suffix(member, (data[id]["suffix"]))
            added = []
            for i in data[id]["reverse_roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.add_roles(role, reason="Left voice channel")
                    added.append(role)
                except:
                    pass
            removed = []
            for i in data[id]["roles"]:
                try:
                    role = member.guild.get_role(int(i))
                    await member.remove_roles(role, reason="Left voice channel")
                    removed.append(role)
                except:
                    pass
            self.client.incr_role_counter("added", len(added))
            self.client.incr_role_counter("removed", len(removed))
            return {"added": added, "removed": removed}
        return {"added": [], "removed": []}

    async def return_data(self):
        return {"added": [], "removed": []}


async def setup(client: VCRolesClient):
    await client.add_cog(VoiceState(client))
