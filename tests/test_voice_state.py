import asyncio
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from weakref import WeakValueDictionary

import discord

voice_module = importlib.import_module("cogs.voicestate")
VoiceState = voice_module.VoiceState
NicknameUpdate = voice_module.NicknameUpdate
QueuedMemberUpdate = voice_module.QueuedMemberUpdate


class MemberUpdateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cog = object.__new__(VoiceState)
        self.cog.client = Mock()
        self.cog.member_locks = WeakValueDictionary()
        self.cog.bot_nicknames = {}
        self.guild = Mock(id=1, owner_id=999)
        self.guild.me.guild_permissions.manage_nicknames = True
        self.guild.me.top_role.position = 10
        self.queued = Mock(id=2, guild=self.guild, display_name="Original")
        self.queued.roles = [discord.Object(id=1), discord.Object(id=50)]
        self.fresh = Mock(id=2, guild=self.guild, display_name="Original")
        self.fresh.top_role.position = 1
        self.fresh.roles = [discord.Object(id=1), discord.Object(id=50)]
        self.fresh.edit = AsyncMock()
        self.guild.fetch_member = AsyncMock(return_value=self.fresh)

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
