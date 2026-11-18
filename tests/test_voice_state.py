import asyncio
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from weakref import WeakValueDictionary

import discord

from tests.test_permission_backoff import forbidden
from utils.permission_backoff import PermissionBackoff

voice_module = importlib.import_module("cogs.voicestate")
VoiceState = voice_module.VoiceState
NicknameUpdate = voice_module.NicknameUpdate
QueuedMemberUpdate = voice_module.QueuedMemberUpdate


class MemberUpdateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cog = object.__new__(VoiceState)
        self.cog.client = Mock()
        self.cog.client.user = SimpleNamespace(id=666)
        self.cog.member_locks = WeakValueDictionary()
        self.cog.bot_nicknames = {}
        self.cog.permission_backoff = PermissionBackoff(self.cog.client)
        self.guild = Mock(id=1, owner_id=999)
        self.guild.me.guild_permissions = discord.Permissions(
            manage_roles=True, manage_nicknames=True
        )
        self.guild.me.top_role.position = 10
        self.queued = Mock(id=2, guild=self.guild, display_name="Original")
        self.queued.roles = [discord.Object(id=1), discord.Object(id=50)]
        self.fresh = Mock(id=2, guild=self.guild, display_name="Original")
        self.fresh.top_role.position = 1
        self.fresh.roles = [discord.Object(id=1), discord.Object(id=50)]
        self.fresh.edit = AsyncMock()
        self.guild.fetch_member = AsyncMock(return_value=self.fresh)
        self.bot_member = SimpleNamespace(
            id=666, _roles=[7], is_timed_out=lambda: False
        )
        self.live_bot_role = SimpleNamespace(
            id=7,
            permissions=discord.Permissions(manage_roles=True, manage_nicknames=True),
        )
        self.guild.fetch_roles = AsyncMock(return_value=[self.live_bot_role])

        async def fetch(member_id):
            if member_id == self.bot_member.id:
                return self.bot_member
            return self.guild.fetch_member.return_value

        self.guild.fetch_member.side_effect = fetch

    async def test_role_only_update_preserves_newer_moderator_nickname(self):
        self.fresh.display_name = "Moderator rename"
        await self.cog.handle_member_edit(
            self.queued, [discord.Object(id=10), discord.Object(id=11)], [], []
        )
        kwargs = self.fresh.edit.call_args.kwargs
        self.assertNotIn("nick", kwargs)
        self.assertEqual({role.id for role in kwargs["roles"]}, {10, 11, 50})

    async def test_stale_suffix_change_does_not_overwrite_newer_nickname(self):
        self.fresh.display_name = "Moderator rename"
        await self.cog.handle_member_edit(
            self.queued,
            [discord.Object(id=10), discord.Object(id=11)],
            [],
            [NicknameUpdate("Original", add_suffix="VC")],
        )
        self.assertNotIn("nick", self.fresh.edit.call_args.kwargs)

    async def test_requested_nickname_change_applies_when_original_name_matches(self):
        await self.cog.handle_member_edit(
            self.queued, [], [], [NicknameUpdate("Original", add_suffix="VC")]
        )
        self.fresh.edit.assert_awaited_once_with(
            nick="Original VC", reason="Joined Voice Channel"
        )

    async def test_single_role_uses_atomic_endpoint_without_member_fetch(self):
        self.queued.add_roles = AsyncMock()
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        self.guild.fetch_member.assert_not_awaited()
        self.queued.add_roles.assert_awaited_once()

    async def test_missing_manage_roles_skips_requests_and_resumes_on_repair(self):
        self.guild.me.guild_permissions.manage_roles = False
        self.queued.add_roles = AsyncMock()
        for _ in range(10):
            await self.cog.handle_member_edit(
                self.queued, [discord.Object(id=10)], [], []
            )
        self.queued.add_roles.assert_not_awaited()
        self.guild.fetch_member.assert_not_awaited()
        self.cog.client.log.assert_called_once()
        self.guild.me.guild_permissions.manage_roles = True
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        self.queued.add_roles.assert_awaited_once()

    async def test_stale_guild_permissions_get_a_real_trial_and_recover(self):
        now = [0.0]
        self.cog.permission_backoff = PermissionBackoff(
            self.cog.client, clock=lambda: now[0]
        )
        self.guild.me.guild_permissions.manage_roles = False
        self.queued.add_roles = AsyncMock()
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        self.queued.add_roles.assert_not_awaited()
        now[0] += 30
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        self.assertEqual(self.queued.add_roles.await_count, 2)

    async def test_noop_nickname_candidates_do_not_consume_guild_recovery_trial(self):
        for case in ("owner", "stale_name", "unchanged", "hierarchy"):
            with self.subTest(case=case):
                now = [0.0]
                self.cog.permission_backoff = PermissionBackoff(
                    self.cog.client, clock=lambda now=now: now[0]
                )
                self.cog.bot_nicknames.clear()
                self.guild.me.guild_permissions.manage_nicknames = False
                self.fresh.edit.reset_mock()
                updates = [NicknameUpdate("Original", add_suffix="VC")]
                await self.cog.handle_member_edit(self.queued, [], [], updates)
                state = self.cog.permission_backoff.states[("guild_nicknames", 1, 1)]
                self.assertEqual(state.failures, 1)

                member_id = 999 if case == "owner" else 3
                expected_name = "Original VC" if case == "unchanged" else "Original"
                current_name = (
                    "Moderator rename" if case == "stale_name" else expected_name
                )
                candidate = Mock(
                    id=member_id, guild=self.guild, display_name=expected_name
                )
                snapshot = Mock(
                    id=member_id, guild=self.guild, display_name=current_name
                )
                snapshot.top_role.position = 10 if case == "hierarchy" else 1
                snapshot.edit = AsyncMock()
                self.guild.fetch_member.return_value = snapshot
                now[0] = 30
                await self.cog.handle_member_edit(
                    candidate, [], [], [NicknameUpdate(expected_name, add_suffix="VC")]
                )
                snapshot.edit.assert_not_awaited()
                self.assertEqual(state.failures, 1)
                self.assertEqual(state.retry_at, 30)
                self.assertFalse(state.probing)
                self.assertIn(
                    ("guild_nicknames", 1, 1), self.cog.permission_backoff.verified
                )

                # The next eligible member can make an HTTP trial at the same
                # time, despite the unchanged negative permission cache.
                self.guild.fetch_member.return_value = self.fresh
                await self.cog.handle_member_edit(self.queued, [], [], updates)
                self.fresh.edit.assert_awaited_once_with(
                    nick="Original VC", reason="Joined Voice Channel"
                )
                self.assertNotIn(
                    ("guild_nicknames", 1, 1), self.cog.permission_backoff.states
                )

    async def test_forbidden_role_write_does_not_block_nickname_or_another_member(self):
        self.queued.add_roles = AsyncMock(side_effect=forbidden())
        self.fresh.add_roles = AsyncMock(side_effect=forbidden())
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        await self.cog.handle_member_edit(
            self.queued,
            [discord.Object(id=10)],
            [],
            [NicknameUpdate("Original", add_suffix="VC")],
        )
        self.queued.add_roles.assert_awaited_once()
        self.fresh.add_roles.assert_not_awaited()
        self.fresh.edit.assert_awaited_once_with(
            nick="Original VC", reason="Joined Voice Channel"
        )
        other = Mock(
            id=3, guild=self.guild, display_name="Other", add_roles=AsyncMock()
        )
        await self.cog.handle_member_edit(other, [discord.Object(id=10)], [], [])
        other.add_roles.assert_awaited_once()

    async def test_nickname_failure_does_not_block_roles(self):
        self.fresh.edit.side_effect = forbidden()
        await self.cog.handle_member_edit(
            self.queued, [], [], [NicknameUpdate("Original", add_suffix="VC")]
        )
        self.queued.add_roles = AsyncMock()
        await self.cog.handle_member_edit(
            self.queued,
            [discord.Object(id=10)],
            [],
            [NicknameUpdate("Original", add_suffix="VC")],
        )
        self.fresh.edit.assert_awaited_once()
        self.queued.add_roles.assert_awaited_once()
        self.assertFalse(self.cog.bot_nicknames)

    async def test_role_hierarchy_repair_resumes_without_waiting_for_cooldown(self):
        role = self.guild.get_role.return_value
        role.is_assignable.return_value = False
        self.queued.add_roles = AsyncMock()
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        self.queued.add_roles.assert_not_awaited()
        role.is_assignable.return_value = True
        await self.cog.handle_member_edit(self.queued, [discord.Object(id=10)], [], [])
        self.queued.add_roles.assert_awaited_once()

    async def test_voice_events_do_not_fetch_members_before_the_retry_gate(self):
        self.cog.member_queues = {}
        self.cog.client.db.get_all_linked_channel = AsyncMock(return_value=[])
        self.cog.generator = Mock(join=AsyncMock(), leave=AsyncMock())
        before = SimpleNamespace(channel=Mock(id=10, category=None))
        after = SimpleNamespace(channel=Mock(id=11, category=None))
        await self.cog.leave(self.queued, before)
        await self.cog.change(self.queued, before, after)
        self.guild.fetch_member.assert_not_awaited()
        self.assertEqual(len(self.cog.member_queues[1]), 2)

    async def test_successful_roles_and_nickname_use_independent_retry_scopes(self):
        self.queued.add_roles = AsyncMock()
        await self.cog.handle_member_edit(
            self.queued,
            [discord.Object(id=10)],
            [],
            [NicknameUpdate("Original", add_suffix="VC")],
        )
        self.guild.fetch_member.assert_awaited_once()
        self.queued.add_roles.assert_awaited_once()
        self.fresh.edit.assert_awaited_once_with(
            nick="Original VC", reason="Joined Voice Channel"
        )

    async def test_moderator_rename_during_bulk_role_write_is_preserved(self):
        renamed = Mock(
            id=2, guild=self.guild, display_name="Moderator rename", edit=AsyncMock()
        )
        self.guild.fetch_member.side_effect = [self.fresh, renamed]
        await self.cog.handle_member_edit(
            self.queued,
            [discord.Object(id=10), discord.Object(id=11)],
            [],
            [NicknameUpdate("Original", add_suffix="VC")],
        )
        self.fresh.edit.assert_awaited_once()
        self.assertNotIn("nick", self.fresh.edit.await_args.kwargs)
        renamed.edit.assert_not_awaited()
        self.assertEqual(self.guild.fetch_member.await_count, 2)

    async def test_concurrent_members_share_bot_permission_probe_and_resume(self):
        now = [0.0]
        self.cog.permission_backoff = PermissionBackoff(
            self.cog.client, clock=lambda: now[0]
        )
        self.guild.me.guild_permissions.manage_roles = False
        roles = [discord.Object(id=10), discord.Object(id=11)]
        await self.cog.handle_member_edit(self.queued, roles, [], [])
        self.guild.fetch_member.assert_not_awaited()
        now[0] += 30
        started, release = asyncio.Event(), asyncio.Event()
        other_fresh = Mock(
            id=3, guild=self.guild, display_name="Other", edit=AsyncMock()
        )
        other_fresh.roles = [discord.Object(id=1), discord.Object(id=50)]

        async def fetch(member_id):
            if member_id == self.bot_member.id:
                started.set()
                await release.wait()
                return self.bot_member
            return self.fresh if member_id == 2 else other_fresh

        self.guild.fetch_member.side_effect = fetch
        trial = asyncio.create_task(
            self.cog.handle_member_edit(self.queued, roles, [], [])
        )
        await asyncio.wait_for(started.wait(), 1)
        other = Mock(id=3, guild=self.guild, display_name="Other")
        waiting = asyncio.create_task(self.cog.handle_member_edit(other, roles, [], []))
        await asyncio.sleep(0)
        self.assertFalse(waiting.done())
        self.guild.fetch_member.assert_awaited_once()
        release.set()
        await asyncio.wait_for(asyncio.gather(trial, waiting), 1)
        self.assertEqual(self.guild.fetch_member.await_count, 3)
        self.guild.fetch_roles.assert_awaited_once()
        self.fresh.edit.assert_awaited_once()
        other_fresh.edit.assert_awaited_once()

    async def test_denied_bot_probe_keeps_later_guild_members_in_cooldown(self):
        now = [0.0]
        self.cog.permission_backoff = PermissionBackoff(
            self.cog.client, clock=lambda: now[0]
        )
        self.guild.me.guild_permissions.manage_roles = False
        roles = [discord.Object(id=10), discord.Object(id=11)]
        await self.cog.handle_member_edit(self.queued, roles, [], [])
        now[0] += 30
        self.guild.fetch_member.side_effect = forbidden()
        await self.cog.handle_member_edit(self.queued, roles, [], [])
        for member_id in range(3, 13):
            other = Mock(id=member_id, guild=self.guild, display_name="Other")
            await self.cog.handle_member_edit(other, roles, [], [])
        self.guild.fetch_member.assert_awaited_once()
        state = self.cog.permission_backoff.states[("guild_roles", 1, 1)]
        self.assertEqual(state.retry_at, 90)

    async def test_member_failures_do_not_extend_guild_permission_cooldown(self):
        for failure in ("nickname", "fetch", "roles"):
            with self.subTest(failure=failure):
                now = [0.0]
                self.cog.permission_backoff = PermissionBackoff(
                    self.cog.client, clock=lambda now=now: now[0]
                )
                self.guild.me.guild_permissions.manage_nicknames = failure == "roles"
                self.guild.me.guild_permissions.manage_roles = failure != "roles"
                self.cog.bot_nicknames.clear()
                self.fresh.edit.reset_mock(side_effect=True)
                other = Mock(id=3, guild=self.guild, display_name="Other")
                healthy = Mock(
                    id=3, guild=self.guild, display_name="Other", edit=AsyncMock()
                )
                healthy.top_role.position = 1
                healthy.roles = [discord.Object(id=1), discord.Object(id=50)]

                async def fetch(member_id, failure=failure, healthy=healthy):
                    if member_id == self.bot_member.id:
                        return self.bot_member
                    if member_id == 2 and failure == "fetch":
                        raise forbidden()
                    return self.fresh if member_id == 2 else healthy

                self.guild.fetch_member.reset_mock()
                self.guild.fetch_member.side_effect = fetch
                self.guild.fetch_roles.reset_mock()
                roles = (
                    [discord.Object(id=10), discord.Object(id=11)]
                    if failure == "roles"
                    else []
                )
                updates = (
                    []
                    if failure == "roles"
                    else [NicknameUpdate("Original", add_suffix="VC")]
                )
                await self.cog.handle_member_edit(self.queued, roles, [], updates)
                now[0] = 30
                if failure != "fetch":
                    self.fresh.edit.side_effect = forbidden()
                await self.cog.handle_member_edit(self.queued, roles, [], updates)
                operation = "guild_roles" if failure == "roles" else "guild_nicknames"
                pending = self.cog.permission_backoff.states[(operation, 1, 1)]
                self.assertEqual((pending.failures, pending.retry_at), (0, 0))

                other_updates = (
                    []
                    if failure == "roles"
                    else [NicknameUpdate("Other", add_suffix="VC")]
                )
                await self.cog.handle_member_edit(other, roles, [], other_updates)
                healthy.edit.assert_awaited_once()
                self.assertNotIn((operation, 1, 1), self.cog.permission_backoff.states)
                self.assertIn((operation, 1, 1), self.cog.permission_backoff.verified)
                # One initial self-check and one immediate read-only recheck;
                # the individual failure never imposes a guild-wide wait.
                self.assertEqual(self.guild.fetch_roles.await_count, 2)
                self.assertEqual(
                    sum(
                        call.args == (666,)
                        for call in self.guild.fetch_member.await_args_list
                    ),
                    2,
                )

    async def test_concurrent_batches_serialize_fetch_and_preserve_previous_roles(self):
        editing = asyncio.Event()
        release = asyncio.Event()
        writes = []

        async def edit(**kwargs):
            writes.append({role.id for role in kwargs["roles"]})
            if len(writes) == 1:
                editing.set()
                await release.wait()
            self.fresh.roles = [discord.Object(id=1), *kwargs["roles"]]

        self.fresh.edit.side_effect = edit
        first = asyncio.create_task(
            self.cog.handle_member_edit(
                self.queued,
                [discord.Object(id=10), discord.Object(id=11)],
                [],
                [],
            )
        )
        await asyncio.wait_for(editing.wait(), 1)
        second = asyncio.create_task(
            self.cog.handle_member_edit(
                self.queued,
                [discord.Object(id=12), discord.Object(id=13)],
                [],
                [],
            )
        )
        await asyncio.sleep(0)
        self.guild.fetch_member.assert_awaited_once()
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 1)
        self.assertEqual(writes, [{10, 11, 50}, {10, 11, 12, 13, 50}])

    async def test_fetch_failure_skips_bulk_write_and_is_logged(self):
        self.guild.fetch_member.side_effect = RuntimeError("unavailable")
        await self.cog.handle_member_edit(
            self.queued, [discord.Object(id=10), discord.Object(id=11)], [], []
        )
        self.fresh.edit.assert_not_awaited()
        self.cog.client.log.assert_called_once()

    async def test_cancelled_lock_waiter_preserves_owner_lock_and_cancellation(self):
        lock = asyncio.Lock()
        await lock.acquire()
        self.cog.member_locks[(self.guild.id, self.queued.id)] = lock
        waiter = asyncio.create_task(
            self.cog.handle_member_edit(
                self.queued, [discord.Object(id=10), discord.Object(id=11)], [], []
            )
        )
        await asyncio.sleep(0)
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        self.assertTrue(lock.locked())
        self.guild.fetch_member.assert_not_awaited()
        self.cog.client.log.assert_not_called()
        lock.release()
        await asyncio.wait_for(
            self.cog.handle_member_edit(
                self.queued, [discord.Object(id=10), discord.Object(id=11)], [], []
            ),
            1,
        )
        self.guild.fetch_member.assert_awaited_once()
        self.assertFalse(lock.locked())

    async def test_overlapping_bot_renames_apply_latest_channel_suffix(self):
        editing = asyncio.Event()
        release = asyncio.Event()
        names = []

        async def edit(**kwargs):
            names.append(kwargs["nick"])
            if len(names) == 1:
                editing.set()
                await release.wait()
            self.fresh.display_name = kwargs["nick"]

        self.fresh.edit.side_effect = edit
        first = asyncio.create_task(
            self.cog.handle_member_edit(
                self.queued, [], [], [NicknameUpdate("Original", add_suffix="A")]
            )
        )
        await asyncio.wait_for(editing.wait(), 1)
        second = asyncio.create_task(
            self.cog.handle_member_edit(
                self.queued,
                [],
                [],
                [NicknameUpdate("Original", remove_suffix="A", add_suffix="B")],
            )
        )
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 1)
        self.assertEqual(names, ["Original A", "Original B"])

    async def test_grouped_join_move_leave_operations_keep_permanent_suffix(self):
        self.cog.client.loop = asyncio.get_running_loop()
        self.cog.edit_tasks = set()
        self.cog.member_queues = {
            1: [
                QueuedMemberUpdate(
                    self.queued,
                    [],
                    [],
                    NicknameUpdate("Original", add_suffix="A", permanent_suffix="VIP"),
                ),
                QueuedMemberUpdate(
                    self.queued,
                    [],
                    [],
                    NicknameUpdate(
                        "Original",
                        remove_suffix="A",
                        add_suffix="B",
                        permanent_suffix="VIP",
                    ),
                ),
                QueuedMemberUpdate(
                    self.queued, [], [], NicknameUpdate("Original", remove_suffix="B")
                ),
            ]
        }
        await self.cog.process_queues()
        await asyncio.gather(*self.cog.edit_tasks)
        self.fresh.edit.assert_awaited_once_with(
            nick="Original VIP", reason="Joined Voice Channel"
        )

    async def test_moderator_rename_after_bot_rename_still_takes_precedence(self):
        self.cog.bot_nicknames[(1, 2)] = "Original A"
        self.fresh.display_name = "Moderator rename"
        await self.cog.handle_member_edit(
            self.queued,
            [],
            [],
            [NicknameUpdate("Original", remove_suffix="A", add_suffix="B")],
        )
        self.fresh.edit.assert_not_awaited()

    async def test_failed_nickname_write_is_not_treated_as_bot_authored(self):
        self.fresh.edit.side_effect = RuntimeError("failed")
        await self.cog.handle_member_edit(
            self.queued, [], [], [NicknameUpdate("Original", add_suffix="A")]
        )
        self.assertFalse(self.cog.bot_nicknames)

    async def test_unload_drains_events_before_flushing_and_awaits_edits(self):
        event_release = asyncio.Event()
        edit_release = asyncio.Event()
        flushed = asyncio.Event()
        event_task = asyncio.create_task(event_release.wait())
        edit_task = asyncio.create_task(edit_release.wait())
        self.cog.unloading = False
        self.cog.event_tasks = {event_task}
        self.cog.edit_tasks = {edit_task}
        self.cog.logging = SimpleNamespace(stop=AsyncMock())

        async def flush():
            self.assertTrue(event_task.done())
            flushed.set()

        self.cog.process_queues = AsyncMock(side_effect=flush)
        self.cog.process_queues.get_task = Mock(return_value=None)
        self.cog.process_queues.cancel = Mock()
        self.cog.reconcile_generators = Mock()
        self.cog.reconcile_generators.get_task.return_value = None
        unloading = asyncio.create_task(self.cog.cog_unload())
        await asyncio.sleep(0)
        self.assertTrue(self.cog.unloading)
        self.cog.process_queues.assert_not_awaited()
        event_release.set()
        await asyncio.wait_for(flushed.wait(), 1)
        self.cog.logging.stop.assert_not_awaited()
        edit_release.set()
        await asyncio.wait_for(unloading, 1)
        self.cog.logging.stop.assert_awaited_once()

    async def test_unload_cancels_event_that_exceeds_shutdown_deadline(self):
        self.cog.SHUTDOWN_TIMEOUT = 0.01
        self.cog.CANCELLATION_GRACE = 0.01
        self.cog.unloading = False

        async def event_with_slow_cleanup():
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                await asyncio.Event().wait()

        event_task = asyncio.create_task(event_with_slow_cleanup())
        edit_task = asyncio.create_task(asyncio.Event().wait())
        self.cog.event_tasks = {event_task}
        self.cog.edit_tasks = {edit_task}
        self.cog.logging = SimpleNamespace(stop=AsyncMock())
        self.cog.process_queues = AsyncMock()
        self.cog.process_queues.get_task = Mock(return_value=None)
        self.cog.process_queues.cancel = Mock()
        self.cog.reconcile_generators = Mock()
        self.cog.reconcile_generators.get_task.return_value = None
        await asyncio.wait_for(self.cog.cog_unload(), 1)
        self.assertTrue(event_task.cancelled())
        self.assertGreaterEqual(event_task.cancelling(), 2)
        self.assertTrue(edit_task.cancelled())
        self.cog.logging.stop.assert_awaited_once()
        self.cog.client.log.assert_called_once()
