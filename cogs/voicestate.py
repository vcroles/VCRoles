import asyncio
import copy
from typing import Collection, Tuple

import discord
import discord.utils as disutils
from discord.ext import commands, tasks
from discord.object import Object

from prisma.enums import LinkType
from utils.client import VCRolesClient
from utils.types import (
    LogLevel,
    MentionableRole,
    SuffixConstructor,
    VoiceStateReturnData,
)
from voicestate.generator import Generator
from voicestate.logging import Logging


class VoiceState(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.generator = Generator(client)
        self.logging = Logging(client)
        self.member_queues: dict[
            int,
            list[Tuple[discord.Member, list[discord.Role], list[discord.Role], str]],
        ] = {}
        self.process_queues.start()

    async def cog_unload(self):
        self.process_queues.cancel()
        self.logging.stop()

        await super().cog_unload()

    @tasks.loop(seconds=5)
    async def process_queues(self):
        try:
            # Create a copy of the member_queues and clear the original
            member_queues = self.member_queues.copy()
            self.member_queues.clear()

            for guild_id, queue in member_queues.items():
                if not queue:
                    continue

                guild = self.client.get_guild(guild_id)
                if not guild:
                    continue

                tasks = []

                # Group the current queue by member
                member_changes = {}
                for member, to_add, to_remove, new_nick in queue:
                    if member.id not in member_changes:
                        member_changes[member.id] = {
                            "member": member,
                            "to_add": [],
                            "to_remove": [],
                            "new_nick": new_nick,
                        }
                    member_changes[member.id]["member"] = member
                    member_changes[member.id]["to_add"].extend(to_add)
                    member_changes[member.id]["to_remove"].extend(to_remove)
                    member_changes[member.id]["new_nick"] = new_nick

                for _member_id, change in member_changes.items():
                    member = change["member"]
                    to_add = change["to_add"]
                    to_remove = change["to_remove"]
                    new_nick = change["new_nick"]

                    # Find the intersection of to_add and to_remove without using sets (since this removes duplicates)
                    # We need to do this to handle if a user is spam switching between channels
                    role_idx = 0
                    while role_idx < len(to_add):
                        role = to_add[role_idx]
                        if role in to_remove:
                            to_add.pop(role_idx)
                            to_remove.remove(role)
                        else:
                            role_idx += 1

                    # Create a task for handling user edit
                    task = asyncio.create_task(
                        self.handle_user_edit(
                            member, set(to_add), set(to_remove), new_nick
                        )
                    )
                    tasks.append(task)

                # Wait for all tasks to complete
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.client.log(LogLevel.ERROR, f"Error processing member queues: {e}")

    @process_queues.before_loop
    async def before_process_queues(self):
        await self.client.wait_until_ready()

    async def queue_member_update(
        self,
        member: discord.Member,
        to_add: list[discord.Role],
        to_remove: list[discord.Role],
        new_nick: str,
    ):
        if member.guild.id not in self.member_queues:
            self.member_queues[member.guild.id] = []
        self.member_queues[member.guild.id].append(
            (member, to_add, to_remove, new_nick)
        )

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        # Make copies of member, before and after to prevent race conditions
        member = copy.copy(member)
        before = copy.copy(before)
        after = copy.copy(after)

        # Joining
        if before.channel is None and after.channel is not None:
            roles_changed, failed_roles = await self.join(member, after)

            if failed_roles:
                self.client.log(
                    LogLevel.INFO,
                    f"Failed to change roles on join: m/{member.id} c/{after.channel.id} g/{member.guild.id} r/({','.join(map(lambda x: str(x.id), failed_roles))})",
                )

            await self.logging.log_join(
                after.channel,
                member,
                roles_changed,
                failed_roles,
            )

        # Leaving
        elif before.channel is not None and after.channel is None:
            roles_changed, failed_roles = await self.leave(member, before)

            if failed_roles:
                self.client.log(
                    LogLevel.INFO,
                    f"Failed to change roles on leave: m/{member.id} c/{before.channel.id} g/{member.guild.id} r/({','.join(map(lambda x: str(x.id), failed_roles))})",
                )

            await self.logging.log_leave(
                before.channel,
                member,
                roles_changed,
                failed_roles,
            )

        # Changing
        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel != after.channel
        ):
            leave_roles_changed, join_roles_changed, failed_roles = await self.change(
                member, before, after
            )

            if failed_roles:
                self.client.log(
                    LogLevel.INFO,
                    f"Failed to change roles on change: m/{member.id} c/{before.channel.id} g/{member.guild.id} r/({','.join(map(lambda x: str(x.id), failed_roles))})",
                )

            await self.logging.log_change(
                before.channel,
                after.channel,
                member,
                leave_roles_changed,
                join_roles_changed,
                failed_roles,
            )

        if (
            isinstance(before.channel, discord.StageChannel)
            and isinstance(after.channel, discord.StageChannel)
            and before.channel.id == after.channel.id
        ):
            # Become Speaker
            if before.suppress and not after.suppress:
                data = await self.client.db.get_channel_linked(
                    before.channel.id, member.guild.id, LinkType.STAGE
                )

                for role_id in data.speakerRoles:
                    role = member.guild.get_role(int(role_id))
                    if not role:
                        continue

                    try:
                        await member.add_roles(role, reason="Became Speaker")
                    except discord.errors.Forbidden:
                        pass
                    except discord.errors.HTTPException:
                        pass

            # Stop Speaker
            elif not before.suppress and after.suppress:
                data = await self.client.db.get_channel_linked(
                    before.channel.id, member.guild.id, LinkType.STAGE
                )

                for role_id in data.speakerRoles:
                    role = member.guild.get_role(int(role_id))
                    if not role:
                        continue

                    try:
                        await member.remove_roles(role, reason="Stopped Speaker")
                    except discord.errors.Forbidden:
                        pass
                    except discord.errors.HTTPException:
                        pass

    async def handle_user_edit(
        self,
        member: discord.Member,
        to_add: Collection[discord.abc.Snowflake],
        to_remove: Collection[discord.abc.Snowflake],
        new_user_nickname: str,
    ):
        new_roles = disutils.MISSING

        if to_add or to_remove:
            new_roles = disutils._unique(  # type: ignore[reportPrivateUsage]
                Object(id=r.id)
                for s in (member.roles[1:], to_add)  # remove @everyone
                for r in s
            )

            for remove_role in to_remove:
                try:
                    new_roles.remove(Object(id=remove_role.id))
                except ValueError:
                    pass

        new_nick = disutils.MISSING

        if new_user_nickname != member.display_name:
            new_nick = new_user_nickname

        if member.guild.owner_id == member.id:
            # The owner can't have their nickname changed
            new_nick = disutils.MISSING

        try:
            await member.edit(
                nick=new_nick,
                roles=new_roles,
                reason="Joined Voice Channel",
            )
        except Exception as e:
            self.client.log(
                LogLevel.ERROR,
                f"Failed to edit member {member.id} ({member.display_name}): {e}",
            )

    async def join(
        self,
        member: discord.Member,
        after: discord.VoiceState,
    ) -> tuple[list[VoiceStateReturnData], list[discord.Role]]:
        if not after.channel:
            # Unreachable.
            return [], []

        links = await self.client.db.get_all_linked_channel(
            member.guild.id,
            after.channel.id,
            after.channel.category.id if after.channel.category else None,
        )

        addable_roles: list[str] = []
        removeable_roles: list[str] = []

        return_data: list[VoiceStateReturnData] = []
        suffix_data = SuffixConstructor()

        for link in links:
            if str(after.channel.id) in link.excludeChannels:
                continue
            addable_roles.extend(link.linkedRoles)
            removeable_roles.extend(link.reverseLinkedRoles)
            return_data.append(
                VoiceStateReturnData(
                    "join",
                    link.type,
                    list(map(MentionableRole, link.linkedRoles)),
                    list(map(MentionableRole, link.reverseLinkedRoles)),
                )
            )
            suffix_data.add(link.type, link.suffix or "")

        # remove duplicates
        addable_roles = list(set(addable_roles))
        removeable_roles = list(set(removeable_roles))

        # if a role appears in both lists, remove both instances
        for role in addable_roles:
            if role in removeable_roles:
                addable_roles.remove(role)
                removeable_roles.remove(role)

        failed_roles: list[discord.Role] = []

        to_add: list[discord.Role] = []
        to_remove: list[discord.Role] = []

        for role_id in addable_roles:
            role = member.guild.get_role(int(role_id))
            if not role:
                continue

            if not role.is_assignable():
                failed_roles.append(role)
                continue

            to_add.append(role)

        for role_id in removeable_roles:
            role = member.guild.get_role(int(role_id))
            if not role:
                continue

            if not role.is_assignable():
                failed_roles.append(role)
                continue

            to_remove.append(role)

        addable_suffix = f"{suffix_data.permanent_suffix + ' ' if suffix_data.permanent_suffix else ''}{suffix_data.suffix}"
        if not member.display_name.endswith(addable_suffix):
            new_user_nickname = f"{member.display_name} {addable_suffix}"
            if len(new_user_nickname) > 32:
                new_user_nickname = member.display_name
        else:
            new_user_nickname = member.display_name

        await self.queue_member_update(member, to_add, to_remove, new_user_nickname)

        self.client.incr_role_counter("added", len(addable_roles))
        self.client.incr_role_counter("removed", len(removeable_roles))

        await self.generator.join(member, after.channel)

        return return_data, list(set(failed_roles))

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
    ) -> tuple[list[VoiceStateReturnData], list[discord.Role]]:
        if not before.channel:
            # Unreachable.
            return [], []

        links = await self.client.db.get_all_linked_channel(
            member.guild.id,
            before.channel.id,
            before.channel.category.id if before.channel.category else None,
        )

        addable_roles: list[str] = []
        removeable_roles: list[str] = []

        return_data: list[VoiceStateReturnData] = []
        suffix_data = SuffixConstructor()

        for link in links:
            if str(before.channel.id) in link.excludeChannels:
                continue
            if link.type == LinkType.PERMANENT:
                continue
            addable_roles.extend(link.reverseLinkedRoles)
            removeable_roles.extend(link.linkedRoles)
            return_data.append(
                VoiceStateReturnData(
                    "leave",
                    link.type,
                    list(map(MentionableRole, link.reverseLinkedRoles)),
                    list(map(MentionableRole, link.linkedRoles)),
                )
            )
            suffix_data.add(link.type, link.suffix or "")

        # remove duplicates
        addable_roles = list(set(addable_roles))
        removeable_roles = list(set(removeable_roles))

        # if a role appears in both lists, remove both instances
        for role in addable_roles:
            if role in removeable_roles:
                addable_roles.remove(role)
                removeable_roles.remove(role)

        failed_roles: list[discord.Role] = []

        try:
            fetched_member = await before.channel.guild.fetch_member(member.id)
        except Exception:
            fetched_member = member

        to_add: list[discord.Role] = []
        to_remove: list[discord.Role] = []

        for role_id in addable_roles:
            role = member.guild.get_role(int(role_id))
            if not role:
                continue

            if not role.is_assignable():
                failed_roles.append(role)
                continue

            to_add.append(role)

        for role_id in removeable_roles:
            role = member.guild.get_role(int(role_id))
            if not role:
                continue

            if not role.is_assignable():
                failed_roles.append(role)
                continue

            to_remove.append(role)

        new_user_nickname = fetched_member.display_name.removesuffix(suffix_data.suffix)

        await self.queue_member_update(
            fetched_member, to_add, to_remove, new_user_nickname
        )

        self.client.incr_role_counter("added", len(addable_roles))
        self.client.incr_role_counter("removed", len(removeable_roles))

        await self.generator.leave(member, before.channel)

        return return_data, list(set(failed_roles))

    async def change(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> tuple[
        list[VoiceStateReturnData], list[VoiceStateReturnData], list[discord.Role]
    ]:
        if not before.channel or not after.channel:
            # Unreachable.
            return [], [], []

        before_links = await self.client.db.get_all_linked_channel(
            member.guild.id,
            before.channel.id,
            before.channel.category.id if before.channel.category else None,
        )

        after_links = await self.client.db.get_all_linked_channel(
            member.guild.id,
            after.channel.id,
            after.channel.category.id if after.channel.category else None,
        )

        addable_roles: list[str] = []
        removeable_roles: list[str] = []

        leave_return_data: list[VoiceStateReturnData] = []
        join_return_data: list[VoiceStateReturnData] = []

        leave_suffix_data = SuffixConstructor()
        join_suffix_data = SuffixConstructor()

        for link in before_links:
            if str(before.channel.id) in link.excludeChannels:
                continue
            if link.type == LinkType.PERMANENT:
                continue
            addable_roles.extend(link.reverseLinkedRoles)
            removeable_roles.extend(link.linkedRoles)
            leave_return_data.append(
                VoiceStateReturnData(
                    "leave",
                    link.type,
                    list(map(MentionableRole, link.reverseLinkedRoles)),
                    list(map(MentionableRole, link.linkedRoles)),
                )
            )
            leave_suffix_data.add(link.type, link.suffix or "")

        for link in after_links:
            if str(after.channel.id) in link.excludeChannels:
                continue
            addable_roles.extend(link.linkedRoles)
            removeable_roles.extend(link.reverseLinkedRoles)
            join_return_data.append(
                VoiceStateReturnData(
                    "join",
                    link.type,
                    list(map(MentionableRole, link.linkedRoles)),
                    list(map(MentionableRole, link.reverseLinkedRoles)),
                )
            )
            join_suffix_data.add(link.type, link.suffix or "")

        # remove duplicates
        addable_roles = list(set(addable_roles))
        removeable_roles = list(set(removeable_roles))

        # if a role appears in both lists, remove both instances
        for role in addable_roles:
            if role in removeable_roles:
                addable_roles.remove(role)
                removeable_roles.remove(role)

        failed_roles: list[discord.Role] = []

        try:
            fetched_member = await before.channel.guild.fetch_member(member.id)
        except Exception:
            fetched_member = member

        to_add: list[discord.Role] = []
        to_remove: list[discord.Role] = []

        for role_id in addable_roles:
            role = member.guild.get_role(int(role_id))
            if not role:
                continue

            if not role.is_assignable():
                failed_roles.append(role)
                continue

            to_add.append(role)

        for role_id in removeable_roles:
            role = member.guild.get_role(int(role_id))
            if not role:
                continue

            if not role.is_assignable():
                failed_roles.append(role)
                continue

            to_remove.append(role)

        removed_leave_suffix = fetched_member.display_name.removesuffix(
            leave_suffix_data.suffix
        )
        addable_suffix = f" {join_suffix_data.permanent_suffix + ' ' if join_suffix_data.permanent_suffix else ''}{join_suffix_data.suffix}"
        if len(removed_leave_suffix + addable_suffix) > 32:
            new_user_nickname = removed_leave_suffix
        else:
            if not removed_leave_suffix.endswith(addable_suffix):
                new_user_nickname = removed_leave_suffix + addable_suffix
            else:
                new_user_nickname = removed_leave_suffix

        await self.queue_member_update(
            fetched_member, to_add, to_remove, new_user_nickname
        )

        self.client.incr_role_counter("added", len(addable_roles))
        self.client.incr_role_counter("removed", len(removeable_roles))

        await self.generator.leave(member, before.channel)
        await self.generator.join(member, after.channel)

        return leave_return_data, join_return_data, list(set(failed_roles))


async def setup(client: VCRolesClient):
    await client.add_cog(VoiceState(client))
