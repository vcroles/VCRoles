import asyncio
import copy
import time
from collections.abc import Collection
from dataclasses import dataclass, field
from weakref import WeakValueDictionary

import discord
import discord.utils as disutils
from cachetools import TTLCache
from discord.ext import commands, tasks
from discord.object import Object
from prisma.enums import LinkType

from utils.client import VCRolesClient
from utils.telemetry import get_telemetry, observed
from utils.types import (
    LogLevel,
    MentionableRole,
    SuffixConstructor,
    VoiceStateReturnData,
)
from voicestate.generator import Generator
from voicestate.logging import Logging


@dataclass(frozen=True)
class NicknameUpdate:
    expected_name: str
    remove_suffix: str = ""
    add_suffix: str = ""
    permanent_suffix: str = ""

    def apply(self, name: str) -> str:
        # Apply suffix changes to the name fetched under the member lock.
        for suffix in (self.remove_suffix, self.add_suffix):
            if suffix:
                name = name.removesuffix(f" {suffix.strip()}")
        base = name
        if self.permanent_suffix and not name.endswith(
            f" {self.permanent_suffix.strip()}"
        ):
            name += f" {self.permanent_suffix.strip()}"
        if self.add_suffix:
            name += f" {self.add_suffix.strip()}"
        return name if len(name) <= 32 else base


@dataclass(frozen=True)
class QueuedMemberUpdate:
    member: discord.Member
    to_add: list[discord.Role]
    to_remove: list[discord.Role]
    nickname: NicknameUpdate
    enqueued_at: float = field(default_factory=time.monotonic)
    span_context: object | None = None


class VoiceState(commands.Cog):
    SHUTDOWN_TIMEOUT = 30
    CANCELLATION_GRACE = 5

    def __init__(self, client: VCRolesClient):
        self.client = client
        self.edit_tasks: set[asyncio.Task] = set()
        self.event_tasks: set[asyncio.Task] = set()
        self.unloading = False
        self.member_locks: WeakValueDictionary[tuple[int, int], asyncio.Lock] = (
            WeakValueDictionary()
        )
        self.bot_nicknames: TTLCache[tuple[int, int], str] = TTLCache(2**15, 3600)
        self.generator = Generator(client)
        self.logging = Logging(client)
        self.member_queues: dict[int, list[QueuedMemberUpdate]] = {}
        self.process_queues.start()
        self.reconcile_generators.start()

    async def cog_unload(self):
        self.unloading = True
        self.process_queues.cancel()
        self.reconcile_generators.cancel()
        loop_tasks = [
            task
            for task in (
                self.process_queues.get_task(),
                self.reconcile_generators.get_task(),
            )
            if task is not None
        ]
        await asyncio.gather(*loop_tasks, return_exceptions=True)

        async def drain():
            try:
                await asyncio.gather(*list(self.event_tasks), return_exceptions=True)
                await self.process_queues()
                await asyncio.gather(*list(self.edit_tasks), return_exceptions=True)
            finally:
                async with asyncio.timeout(self.CANCELLATION_GRACE):
                    await self.logging.stop()

        draining = asyncio.create_task(drain())
        _, pending = await asyncio.wait({draining}, timeout=self.SHUTDOWN_TIMEOUT)
        if pending:
            self.client.log(
                LogLevel.ERROR,
                "Voice-state shutdown timed out; cancelling pending work",
                event="voice_state_shutdown_timeout",
                event_tasks=len(self.event_tasks),
                edit_tasks=len(self.edit_tasks),
            )
            # The normal drain may still be waiting on events and never reach
            # its edit phase. Cancel both sets independently of that phase.
            workers = set(self.event_tasks) | set(self.edit_tasks)
            draining.cancel()
            for task in workers:
                if not task.done() and not task.cancelling():
                    task.cancel()
            _, pending = await asyncio.wait(
                {draining, *workers}, timeout=self.CANCELLATION_GRACE
            )
            for task in pending:
                task.cancel()
        else:
            workers = set()
        result = await asyncio.gather(draining, *workers, return_exceptions=True)
        if isinstance(result[0], Exception):
            self.client.log(
                LogLevel.ERROR,
                "Voice-state shutdown failed",
                error=result[0],
                event="voice_state_shutdown_failed",
            )

        await super().cog_unload()

    @tasks.loop(minutes=5)
    async def reconcile_generators(self):
        try:
            await self.generator.reconcile()
        except Exception as error:
            self.client.log(
                LogLevel.ERROR,
                "Generator reconciliation failed",
                error=error,
                event="generator_reconcile_loop_failed",
            )

    @reconcile_generators.before_loop
    async def before_reconcile_generators(self):
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_shard_disconnect(self, shard_id: int):
        self.generator.shard_disconnected(shard_id)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id: int):
        self.generator.shard_available(shard_id)

    @commands.Cog.listener()
    async def on_shard_resumed(self, shard_id: int):
        self.generator.shard_available(shard_id)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        if before.is_obfuscated() != after.is_obfuscated():
            self.generator.channel_visibility_changed(after)

    @tasks.loop(seconds=5)
    async def process_queues(self):
        start_time = time.perf_counter()
        processed_members = 0

        try:
            # Create a copy of the member_queues and clear the original
            member_queues = self.member_queues.copy()
            self.member_queues.clear()

            for guild_id, queue in member_queues.items():
                if not queue:
                    continue

                guild = self.client.get_guild(guild_id)
                if not guild:
                    get_telemetry().queue_finished(
                        [update.enqueued_at for update in queue], "discarded"
                    )
                    continue

                # Group the current queue by member
                member_changes = {}
                for update in queue:
                    member, to_add, to_remove, new_nick = (
                        update.member,
                        update.to_add,
                        update.to_remove,
                        update.nickname,
                    )
                    if member.id not in member_changes:
                        member_changes[member.id] = {
                            "member": member,
                            "to_add": [],
                            "to_remove": [],
                            "nickname_updates": [],
                            "updates": [],
                        }
                    member_changes[member.id]["member"] = member
                    member_changes[member.id]["to_add"].extend(to_add)
                    member_changes[member.id]["to_remove"].extend(to_remove)
                    member_changes[member.id]["nickname_updates"].append(new_nick)
                    member_changes[member.id]["updates"].append(update)

                for _member_id, change in member_changes.items():
                    member = change["member"]
                    to_add = change["to_add"]
                    to_remove = change["to_remove"]
                    nickname_updates = change["nickname_updates"]

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
                    task = self.client.loop.create_task(
                        self._run_member_edit(
                            member,
                            set(to_add),
                            set(to_remove),
                            nickname_updates,
                            change["updates"],
                        )
                    )
                    self.edit_tasks.add(task)
                    task.add_done_callback(self.edit_tasks.discard)

                    processed_members += 1

        except Exception as e:
            self.client.log(
                LogLevel.ERROR,
                "Error processing member queues",
                error=e,
                event="member_queue_failed",
                processed_members=processed_members,
            )

        end_time = time.perf_counter()
        self.client.log(
            LogLevel.INFO,
            f"Processed {processed_members} member queues in {end_time - start_time:.2f} seconds. {len(asyncio.all_tasks(self.client.loop))} tasks in global event loop",
        )

    @process_queues.before_loop
    async def before_process_queues(self):
        await self.client.wait_until_ready()

    async def queue_member_update(
        self,
        member: discord.Member,
        to_add: list[discord.Role],
        to_remove: list[discord.Role],
        new_nick: NicknameUpdate,
    ):
        if member.guild.id not in self.member_queues:
            self.member_queues[member.guild.id] = []
        self.member_queues[member.guild.id].append(
            QueuedMemberUpdate(
                member,
                to_add,
                to_remove,
                new_nick,
                span_context=get_telemetry().capture_context(),
            )
        )

    async def _run_member_edit(
        self, member, to_add, to_remove, nickname_updates, updates
    ):
        telemetry = get_telemetry()
        times = [update.enqueued_at for update in updates]
        with telemetry.operation(
            "member_edit",
            "apply_batch",
            links=[update.span_context for update in updates],
            root=True,
        ) as state:
            telemetry.queue_started(times)
            try:
                await self.handle_member_edit(
                    member, to_add, to_remove, nickname_updates
                )
            except asyncio.CancelledError:
                if state is not None:
                    state.outcome = "cancelled"
                raise
            except Exception as error:
                telemetry.failure(error)
                raise
            finally:
                telemetry.queue_finished(
                    times, state.outcome if state is not None else "success"
                )

    @commands.Cog.listener()
    @observed("voice_state")
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if self.unloading:
            return
        task = asyncio.current_task()
        if task is not None:
            self.event_tasks.add(task)
        try:
            await self.handle_voice_state_update(member, before, after)
        except Exception as error:
            self.client.log(
                LogLevel.ERROR,
                "Voice state update failed",
                error=error,
                event="voice_state_update_failed",
                guild_id=member.guild.id,
                shard_id=member.guild.shard_id,
                member_id=member.id,
                before_channel_id=before.channel.id if before.channel else None,
                after_channel_id=after.channel.id if after.channel else None,
            )
        finally:
            if task is not None:
                self.event_tasks.discard(task)

    @observed("voice_state")
    async def handle_voice_state_update(
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
                    LogLevel.DEBUG,
                    f"Failed to change roles on join: m/{member.id} c/{
                        after.channel.id
                    } g/{member.guild.id} r/({
                        ','.join(map(lambda x: str(x.id), failed_roles))
                    })",
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
                    LogLevel.DEBUG,
                    f"Failed to change roles on leave: m/{member.id} c/{
                        before.channel.id
                    } g/{member.guild.id} r/({
                        ','.join(map(lambda x: str(x.id), failed_roles))
                    })",
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
                    LogLevel.DEBUG,
                    f"Failed to change roles on change: m/{member.id} c/{
                        before.channel.id
                    } g/{member.guild.id} r/({
                        ','.join(map(lambda x: str(x.id), failed_roles))
                    })",
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

    async def handle_member_edit(
        self,
        member: discord.Member,
        to_add: Collection[discord.abc.Snowflake],
        to_remove: Collection[discord.abc.Snowflake],
        nickname_updates: Collection[NicknameUpdate],
    ):
        key = (member.guild.id, member.id)
        lock = self.member_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self.member_locks[key] = lock
        with get_telemetry().operation("member_edit", "wait_for_lock"):
            await lock.acquire()
        try:
            try:
                await self._handle_member_edit(
                    member, to_add, to_remove, nickname_updates
                )
            except Exception as error:
                get_telemetry().failure(error)
                self.client.log(
                    LogLevel.ERROR,
                    "Member update failed",
                    error=error,
                    event="member_update_failed",
                    guild_id=member.guild.id,
                    shard_id=member.guild.shard_id,
                    member_id=member.id,
                    phase="fetch_or_dispatch",
                )
        finally:
            lock.release()

    @observed("member_edit")
    async def _handle_member_edit(
        self,
        member: discord.Member,
        to_add: Collection[discord.abc.Snowflake],
        to_remove: Collection[discord.abc.Snowflake],
        nickname_updates: Collection[NicknameUpdate],
    ):
        key = (member.guild.id, member.id)
        nickname_requested = any(
            update.remove_suffix or update.add_suffix or update.permanent_suffix
            for update in nickname_updates
        )
        if len(to_add) + len(to_remove) > 1 or nickname_requested:
            member = await member.guild.fetch_member(member.id)

        expected_names = {update.expected_name for update in nickname_updates}
        bot_name = self.bot_nicknames.get(key)
        name_is_current = (
            member.display_name in expected_names or member.display_name == bot_name
        )
        new_user_nickname = member.display_name
        if nickname_requested and name_is_current:
            for update in nickname_updates:
                new_user_nickname = update.apply(new_user_nickname)

        changing_username = (
            nickname_requested
            and name_is_current
            and new_user_nickname != member.display_name
            # The owner can't have their nickname changed
            and member.guild.owner_id != member.id
            # Check we have permission to change the nickname
            and member.guild.me.guild_permissions.manage_nicknames
            # Check that our role is above the member's role
            and member.top_role.position < member.guild.me.top_role.position
        )

        new_roles = disutils.MISSING

        if to_add or to_remove:
            new_roles = disutils._unique(
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

        if changing_username:
            new_nick = new_user_nickname

        if changing_username and (to_add or to_remove):
            # Use the member edit endpoint to update the user
            try:
                await member.edit(
                    nick=new_nick,
                    roles=new_roles,
                    reason="Joined Voice Channel",
                )
                self.bot_nicknames[key] = new_nick
            except Exception as e:
                get_telemetry().failure(e)
                self.client.log(
                    LogLevel.ERROR,
                    "Member update failed",
                    error=e,
                    event="member_update_failed",
                    guild_id=member.guild.id,
                    shard_id=member.guild.shard_id,
                    member_id=member.id,
                    action="username+-roles",
                    add_role_ids=[role.id for role in to_add],
                    remove_role_ids=[role.id for role in to_remove],
                )
        elif changing_username:
            # Use the member edit endpoint to update the nickname
            try:
                await member.edit(
                    nick=new_nick,
                    reason="Joined Voice Channel",
                )
                self.bot_nicknames[key] = new_nick
            except Exception as e:
                get_telemetry().failure(e)
                self.client.log(
                    LogLevel.ERROR,
                    "Member update failed",
                    error=e,
                    event="member_update_failed",
                    guild_id=member.guild.id,
                    shard_id=member.guild.shard_id,
                    member_id=member.id,
                    action="username",
                    add_role_ids=[role.id for role in to_add],
                    remove_role_ids=[role.id for role in to_remove],
                )
        elif to_add or to_remove:
            if len(to_add) + len(to_remove) > 1:
                # Use the member edit endpoint to update the roles (multiple changes)
                try:
                    await member.edit(
                        roles=new_roles,
                        reason="Joined Voice Channel",
                    )
                except Exception as e:
                    get_telemetry().failure(e)
                    self.client.log(
                        LogLevel.ERROR,
                        "Member update failed",
                        error=e,
                        event="member_update_failed",
                        guild_id=member.guild.id,
                        shard_id=member.guild.shard_id,
                        member_id=member.id,
                        action="+-roles",
                        add_role_ids=[role.id for role in to_add],
                        remove_role_ids=[role.id for role in to_remove],
                    )
            elif len(to_add) == 1:
                # Use the add member role endpoint to add roles
                try:
                    await member.add_roles(*to_add, reason="Joined Voice Channel")
                except Exception as e:
                    get_telemetry().failure(e)
                    self.client.log(
                        LogLevel.ERROR,
                        "Member update failed",
                        error=e,
                        event="member_update_failed",
                        guild_id=member.guild.id,
                        shard_id=member.guild.shard_id,
                        member_id=member.id,
                        action="+roles",
                        add_role_ids=[role.id for role in to_add],
                        remove_role_ids=[role.id for role in to_remove],
                    )
            elif len(to_remove) == 1:
                # Use the remove member role endpoint to remove roles
                try:
                    await member.remove_roles(*to_remove, reason="Joined Voice Channel")
                except Exception as e:
                    get_telemetry().failure(e)
                    self.client.log(
                        LogLevel.ERROR,
                        "Member update failed",
                        error=e,
                        event="member_update_failed",
                        guild_id=member.guild.id,
                        shard_id=member.guild.shard_id,
                        member_id=member.id,
                        action="-roles",
                        add_role_ids=[role.id for role in to_add],
                        remove_role_ids=[role.id for role in to_remove],
                    )
        else:
            # No changes needed
            # self.client.log(
            #     LogLevel.DEBUG,
            #     f"No changes required for member {member.id} ({member.display_name})",
            # )
            pass

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

        await self.queue_member_update(
            member,
            to_add,
            to_remove,
            NicknameUpdate(
                member.display_name,
                add_suffix=suffix_data.suffix,
                permanent_suffix=suffix_data.permanent_suffix,
            ),
        )

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

        await self.queue_member_update(
            fetched_member,
            to_add,
            to_remove,
            NicknameUpdate(
                fetched_member.display_name, remove_suffix=suffix_data.suffix
            ),
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

        await self.queue_member_update(
            fetched_member,
            to_add,
            to_remove,
            NicknameUpdate(
                fetched_member.display_name,
                remove_suffix=leave_suffix_data.suffix,
                add_suffix=join_suffix_data.suffix,
                permanent_suffix=join_suffix_data.permanent_suffix,
            ),
        )

        self.client.incr_role_counter("added", len(addable_roles))
        self.client.incr_role_counter("removed", len(removeable_roles))

        await self.generator.leave(member, before.channel)
        await self.generator.join(member, after.channel)

        return leave_return_data, join_return_data, list(set(failed_roles))


async def setup(client: VCRolesClient):
    await client.add_cog(VoiceState(client))
