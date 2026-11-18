import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
from prisma.enums import VoiceGeneratorOption, VoiceGeneratorType

from voicestate.generator import Generator


def http_error(error_type=discord.Forbidden):
    return error_type(SimpleNamespace(status=403, reason="Forbidden"), "failed")


class GeneratorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        audit = patch("voicestate.generator.audit_event")
        self.audit = audit.start()
        self.addCleanup(audit.stop)
        self.now = 1000.0
        timer = patch("voicestate.generator.monotonic", side_effect=lambda: self.now)
        timer.start()
        self.addCleanup(timer.stop)
        self.guild = Mock(id=1, shard_id=0, unavailable=False)
        self.voice = Mock(spec=discord.VoiceChannel, id=10, guild=self.guild)
        self.voice.members = []
        self.voice.voice_states = {}
        self.voice.is_obfuscated.return_value = False
        self.voice.delete = AsyncMock()
        self.text = Mock(spec=discord.TextChannel, id=20, guild=self.guild)
        self.text.delete = AsyncMock()
        self.text.is_obfuscated.return_value = False
        self.text.send = AsyncMock()
        self.text.set_permissions = AsyncMock()
        self.text.overwrites_for.return_value = discord.PermissionOverwrite()
        self.channels = {10: self.voice, 20: self.text}
        self.guild.get_channel.side_effect = self.channels.get
        self.guild.fetch_channel = AsyncMock(side_effect=http_error(discord.NotFound))
        self.settings = SimpleNamespace(
            guildId="1",
            generatorId="2",
            hideAtLimit=False,
            channelLimit=1,
            restrictRole=None,
            defaultRole=None,
            defaultOptions=[],
            openChannels=[],
            type=VoiceGeneratorType.DEFAULT,
            defaultUserLimit=0,
        )
        self.record = SimpleNamespace(
            id="record",
            VoiceGenerator=self.settings,
            channelId="10",
            textChannelId="20",
            voiceGeneratorId="generator",
        )
        self.db = Mock()
        self.db.db.generatedchannel.find_many = AsyncMock(return_value=[self.record])
        self.db.delete_generated_channel = AsyncMock()
        self.db.get_generated_channel = AsyncMock(return_value=None)
        self.db.get_generator = AsyncMock(return_value=self.settings)
        self.db.create_generated_channel = AsyncMock()
        self.db.update_generated_channel = AsyncMock()
        self.client = Mock(db=self.db, is_ready=Mock(return_value=True))
        self.client.get_guild.return_value = self.guild
        self.client.get_channel.side_effect = self.channels.get
        self.shard = Mock(is_closed=Mock(return_value=False))
        self.client.get_shard.return_value = self.shard
        self.generator = Generator(self.client)

    async def sweep_twice(self):
        await self.generator.reconcile()
        self.now += 61
        await self.generator.reconcile()

    async def test_empty_channel_requires_two_healthy_observations(self):
        await self.generator.reconcile()
        self.voice.delete.assert_not_awaited()
        self.now += 61
        await self.generator.reconcile()
        self.voice.delete.assert_awaited_once()
        self.text.delete.assert_awaited_once()
        self.db.delete_generated_channel.assert_awaited_once_with(10)

    async def test_audit_intent_precedes_delete_and_records_reason_and_outcome(self):
        async def deleted(**kwargs):
            intent = self.audit.call_args
            self.assertEqual(intent.args[0], "generator_channel_delete_requested")
            self.assertEqual(intent.kwargs["channel_id"], self.text.id)
            self.assertEqual(intent.kwargs["reason"], "test_cleanup")
            self.assertEqual(intent.kwargs["occupants"], 0)

        self.text.delete.side_effect = deleted
        await self.generator._cleanup(self.voice, self.text, reason="test_cleanup")
        events = [call.args[0] for call in self.audit.call_args_list]
        self.assertEqual(
            events,
            [
                "generator_channel_delete_requested",
                "generator_channel_delete_completed",
                "generator_channel_delete_requested",
                "generator_channel_delete_completed",
                "generator_record_delete_requested",
                "generator_record_deleted",
            ],
        )
        self.assertEqual(
            len({call.kwargs["operation_id"] for call in self.audit.call_args_list}), 1
        )

    async def test_failed_audit_intent_prevents_channel_deletion(self):
        self.audit.side_effect = OSError("audit volume is full")
        with self.assertRaises(OSError):
            await self.generator._cleanup(self.voice, self.text)
        self.text.delete.assert_not_awaited()
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_occupied_channel_is_never_deleted(self):
        self.voice.voice_states = {99: Mock()}
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_real_channel_with_uncached_occupant_is_never_deleted(self):
        self.guild._voice_states = {}
        self.guild.get_member.return_value = None
        voice = discord.VoiceChannel(
            state=Mock(),
            guild=self.guild,
            data={
                "id": "10",
                "name": "Generated",
                "position": 0,
                "bitrate": 64000,
                "user_limit": 0,
                "permission_overwrites": [],
            },
        )
        self.guild._voice_states[99] = SimpleNamespace(channel=voice)
        self.assertEqual(voice.members, [])
        self.assertIn(99, voice.voice_states)
        self.channels[10] = voice
        await self.sweep_twice()
        self.assertFalse(await self.generator._cleanup(voice, self.text))
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_disconnected_shard_is_never_cleaned(self):
        self.shard.is_closed.return_value = True
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_unknown_shard_is_never_cleaned(self):
        self.client.get_shard.return_value = None
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()

    async def test_unavailable_guild_is_never_cleaned(self):
        self.guild.unavailable = True
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()

    async def test_resume_waits_and_discards_pre_disconnect_empty_observation(self):
        await self.generator.reconcile()
        self.generator.shard_disconnected(0)
        self.now += 100
        await self.generator.reconcile()
        self.voice.delete.assert_not_awaited()
        self.generator.shard_available(0)
        await self.generator.reconcile()
        self.now += 61
        await self.generator.reconcile()
        self.voice.delete.assert_not_awaited()
        self.now += 61
        await self.generator.reconcile()
        self.voice.delete.assert_awaited_once()

    async def test_occupancy_between_sweeps_resets_empty_observation(self):
        await self.generator.reconcile()
        self.now += 61
        self.voice.voice_states = {99: Mock()}
        await self.generator.reconcile()
        self.voice.members = []
        self.voice.voice_states = {}
        await self.generator.reconcile()
        self.voice.delete.assert_not_awaited()

    async def test_cache_miss_that_exists_in_rest_keeps_record_and_channel(self):
        del self.channels[10]
        self.guild.fetch_channel.side_effect = None
        self.guild.fetch_channel.return_value = self.voice
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_confirmed_missing_voice_deletes_companion_and_record(self):
        del self.channels[10]
        await self.sweep_twice()
        self.text.delete.assert_awaited_once()
        self.db.delete_generated_channel.assert_awaited_once_with("10")

    async def test_rest_failure_does_not_treat_channel_as_missing(self):
        del self.channels[10]
        self.guild.fetch_channel.side_effect = http_error()
        await self.sweep_twice()
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_failed_deletion_retains_database_record_for_retry(self):
        self.text.delete.side_effect = http_error()
        await self.sweep_twice()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_forbidden_cleanup_backs_off_then_recovers_without_cache_change(self):
        self.text.delete.side_effect = http_error()
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        for _ in range(20):
            self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.text.delete.assert_awaited_once()
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
        self.text.delete.side_effect = None
        self.now += 30
        self.assertTrue(await self.generator._cleanup(self.voice, self.text))
        self.assertEqual(self.text.delete.await_count, 2)
        self.voice.delete.assert_awaited_once()
        self.db.delete_generated_channel.assert_awaited_once()

    async def test_connect_permission_repair_resumes_cleanup_before_deadline(self):
        permissions = self.voice.permissions_for.return_value
        permissions.value = 1
        permissions.connect = False
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.text.delete.assert_not_awaited()
        self.voice.delete.assert_not_awaited()
        permissions.connect = True
        permissions.value = 2
        self.assertTrue(await self.generator._cleanup(self.voice, self.text))
        self.voice.delete.assert_awaited_once()

    async def test_negative_channel_cache_does_not_prevent_due_http_trial(self):
        self.voice.permissions_for.return_value.connect = False
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.now += 30
        self.assertTrue(await self.generator._cleanup(self.voice, self.text))
        self.voice.delete.assert_awaited_once()

    async def test_missing_voice_fetch_uses_a_scoped_cooldown(self):
        del self.channels[10]
        self.guild.fetch_channel.side_effect = http_error()
        for _ in range(20):
            await self.generator.reconcile()
        self.guild.fetch_channel.assert_awaited_once_with(10)
        self.db.delete_generated_channel.assert_not_awaited()
        self.now += 30
        self.guild.fetch_channel.side_effect = http_error(discord.NotFound)
        await self.generator.reconcile()
        self.now += 61
        await self.generator.reconcile()
        self.db.delete_generated_channel.assert_awaited_once_with("10")

    async def test_one_failed_channel_does_not_block_another_cleanup(self):
        self.text.delete.side_effect = http_error()
        await self.generator._cleanup(self.voice, self.text)
        other = Mock(spec=discord.VoiceChannel, id=30, guild=self.guild)
        other.is_obfuscated.return_value = False
        other.voice_states = {}
        other.delete = AsyncMock()
        self.assertTrue(await self.generator._cleanup(other, None))
        other.delete.assert_awaited_once()

    async def test_companion_fetch_failure_is_not_interpreted_as_absence(self):
        del self.channels[20]
        self.guild.fetch_channel.side_effect = http_error()
        await self.sweep_twice()
        for _ in range(10):
            await self.generator.reconcile()
        self.guild.fetch_channel.assert_awaited_once_with(20)
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_member_joining_during_text_delete_preserves_voice_and_record(self):
        async def joined(**kwargs):
            self.voice.voice_states = {99: Mock()}

        self.text.delete.side_effect = joined
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_disconnect_during_delete_preserves_remaining_channel_and_record(
        self,
    ):
        async def disconnected(**kwargs):
            self.shard.is_closed.return_value = True

        self.text.delete.side_effect = disconnected
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    def member_and_trigger(self):
        trigger = Mock(spec=discord.VoiceChannel, id=2, guild=self.guild)
        trigger.is_obfuscated.return_value = False
        member = Mock(id=3, guild=self.guild, display_name="Member")
        member.voice = SimpleNamespace(channel=trigger)
        member.move_to = AsyncMock()
        self.guild.create_voice_channel = AsyncMock(return_value=self.voice)
        self.guild.create_text_channel = AsyncMock(return_value=self.text)
        return member, trigger

    async def test_concurrent_creations_respect_generator_limit(self):
        first, trigger = self.member_and_trigger()
        second = Mock(id=4, guild=self.guild, display_name="Second")
        second.voice = SimpleNamespace(channel=trigger)
        second.move_to = AsyncMock()

        async def record_created(*args):
            await asyncio.sleep(0)
            self.settings.openChannels.append(self.record)

        self.db.create_generated_channel.side_effect = record_created
        await asyncio.gather(
            self.generator.join(first, trigger), self.generator.join(second, trigger)
        )
        self.guild.create_voice_channel.assert_awaited_once()
        first.move_to.assert_awaited_once_with(self.voice)
        second.move_to.assert_awaited_once_with(None)

    async def test_move_failure_defers_cleanup_until_outcome_can_be_observed(self):
        member, trigger = self.member_and_trigger()
        self.settings.defaultOptions = [VoiceGeneratorOption.TEXT]
        member.move_to.side_effect = http_error()
        with self.assertRaises(discord.Forbidden):
            await self.generator.join(member, trigger)
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
        self.assertIn(self.voice.id, self.generator.recent_channels)
        # Once the grace period expires, repeated healthy empty observations
        # may recover a genuinely abandoned channel.
        self.generator.recent_channels.clear()
        await self.sweep_twice()
        self.voice.delete.assert_awaited_once()

    async def test_accepted_move_with_delayed_gateway_event_never_rolls_back(self):
        member, trigger = self.member_and_trigger()
        self.settings.defaultOptions = [VoiceGeneratorOption.TEXT]
        member.move_to.side_effect = OSError("Response lost after accepted move")
        with self.assertRaises(OSError):
            await self.generator.join(member, trigger)
        self.assertFalse(self.voice.voice_states)
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
        self.voice.voice_states = {member.id: SimpleNamespace(channel=self.voice)}
        self.generator.recent_channels.clear()
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()

    async def test_move_error_after_member_arrives_does_not_delete_occupied_channel(
        self,
    ):
        member, trigger = self.member_and_trigger()

        async def moved_but_response_failed(channel):
            self.voice.voice_states = {member.id: Mock()}
            raise http_error()

        member.move_to.side_effect = moved_but_response_failed
        with self.assertRaises(discord.Forbidden):
            await self.generator.join(member, trigger)
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_database_failure_during_creation_does_not_leave_voice_channel(self):
        member, trigger = self.member_and_trigger()
        self.db.create_generated_channel.side_effect = RuntimeError("database failed")
        with self.assertRaises(RuntimeError):
            await self.generator.join(member, trigger)
        self.voice.delete.assert_awaited_once()
        member.move_to.assert_not_awaited()

    async def test_cancelled_move_preserves_persisted_channels_until_reconciliation(
        self,
    ):
        member, trigger = self.member_and_trigger()
        self.settings.defaultOptions = [VoiceGeneratorOption.TEXT]
        moving = asyncio.Event()

        async def move(channel):
            moving.set()
            await asyncio.Event().wait()

        member.move_to.side_effect = move
        task = asyncio.create_task(self.generator.join(member, trigger))
        await asyncio.wait_for(moving.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def check_cancelled_creation_response(self, phase):
        member, trigger = self.member_and_trigger()
        self.settings.defaultOptions = [VoiceGeneratorOption.TEXT]
        creating = asyncio.Event()
        release = asyncio.Event()

        async def delayed_response(*args, **kwargs):
            creating.set()
            await release.wait()
            return self.text if phase == "text" else self.voice

        if phase == "voice":
            self.guild.create_voice_channel.side_effect = delayed_response
        elif phase == "clone":
            self.settings.type = VoiceGeneratorType.CLONED
            trigger.clone = AsyncMock(side_effect=delayed_response)
        elif phase == "text":
            self.guild.create_text_channel.side_effect = delayed_response
        else:
            self.db.create_generated_channel.side_effect = delayed_response
        task = asyncio.create_task(self.generator.join(member, trigger))
        await asyncio.wait_for(creating.wait(), 1)
        task.cancel()
        try:
            await asyncio.sleep(0)
            self.assertFalse(task.done())
            self.voice.delete.assert_not_awaited()
        finally:
            release.set()
        with self.assertRaises(asyncio.CancelledError):
            await asyncio.wait_for(task, 1)
        self.db.create_generated_channel.assert_awaited_once()
        self.db.update_generated_channel.assert_awaited_once_with(
            self.voice.id, text_channel_id=str(self.text.id)
        )
        self.voice.delete.assert_awaited_once()
        self.text.delete.assert_awaited_once()
        member.move_to.assert_not_awaited()

    async def test_cancellation_waits_for_voice_creation_response_and_record(self):
        await self.check_cancelled_creation_response("voice")

    async def test_cancellation_waits_for_clone_response_and_record(self):
        await self.check_cancelled_creation_response("clone")

    async def test_cancellation_waits_for_text_creation_response_and_record(self):
        await self.check_cancelled_creation_response("text")

    async def test_cancellation_waits_for_database_creation_response(self):
        await self.check_cancelled_creation_response("record")

    async def test_member_leaving_while_waiting_for_lock_creates_nothing(self):
        member, trigger = self.member_and_trigger()
        lock = self.generator.lock(self.guild.id, trigger.id)
        async with lock:
            task = asyncio.create_task(self.generator.join(member, trigger))
            await asyncio.sleep(0)
            member.voice = None
        await task
        self.guild.create_voice_channel.assert_not_awaited()

    async def test_restriction_and_limit_disconnects_propagate_cancellation(self):
        for limited in (False, True):
            with self.subTest(limited=limited):
                member, trigger = self.member_and_trigger()
                self.settings.restrictRole = None if limited else "99"
                self.settings.openChannels = [self.record] if limited else []
                member.move_to.side_effect = asyncio.CancelledError()
                with self.assertRaises(asyncio.CancelledError):
                    await self.generator.join(member, trigger)
                self.guild.create_voice_channel.assert_not_awaited()

    async def test_missing_text_cache_is_resolved_before_normal_leave_cleanup(self):
        member, _ = self.member_and_trigger()
        del self.channels[20]
        self.guild.fetch_channel.side_effect = None
        self.guild.fetch_channel.return_value = self.text
        await self.generator._leave(member, self.voice, self.record)
        self.text.delete.assert_awaited_once()
        self.voice.delete.assert_awaited_once()

    async def test_inaccessible_text_channel_preserves_voice_and_record(self):
        member, _ = self.member_and_trigger()
        del self.channels[20]
        self.guild.fetch_channel.side_effect = http_error()
        with self.assertRaises(discord.Forbidden):
            await self.generator._leave(member, self.voice, self.record)
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_wrong_type_companion_channel_is_not_deleted(self):
        self.channels[20] = self.voice
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_text_access_updates_only_the_joining_member(self):
        member, _ = self.member_and_trigger()
        member.voice.channel = self.voice
        self.db.get_generated_channel.return_value = self.record
        self.db.get_generator.return_value = None
        await self.generator.join(member, self.voice)
        self.text.set_permissions.assert_awaited_once()
        self.text.edit.assert_not_called()

    async def test_delayed_leave_does_not_revoke_access_after_member_rejoins(self):
        member, _ = self.member_and_trigger()
        member.voice.channel = self.voice
        self.voice.voice_states = {member.id: Mock()}
        await self.generator._leave(member, self.voice, self.record)
        self.text.set_permissions.assert_not_awaited()
        self.voice.delete.assert_not_awaited()

    async def test_hidden_voice_channel_preserves_record_and_companion(self):
        self.voice.is_obfuscated.return_value = True
        await self.sweep_twice()
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()
        self.guild.fetch_channel.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
        self.assertNotIn(self.voice.id, self.generator.empty_channels)
        notices = [
            call
            for call in self.client.log.call_args_list
            if call.kwargs.get("event") == "generator_channel_obfuscated"
        ]
        self.assertEqual(len(notices), 1)

    async def test_hidden_companion_prevents_even_a_direct_cleanup(self):
        self.text.is_obfuscated.return_value = True
        self.generator.empty_channels[self.voice.id] = (0, self.now - 120)
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.voice.delete.assert_not_awaited()
        self.text.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
        self.assertNotIn(self.voice.id, self.generator.empty_channels)
        self.audit.assert_not_called()

    async def test_visibility_loss_during_text_delete_preserves_voice_and_record(self):
        async def hidden(**kwargs):
            self.voice.is_obfuscated.return_value = True

        self.text.delete.side_effect = hidden
        self.assertFalse(await self.generator._cleanup(self.voice, self.text))
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()

    async def test_visibility_recovery_requires_new_empty_observations(self):
        await self.generator.reconcile()
        self.voice.is_obfuscated.return_value = True
        self.generator.channel_visibility_changed(self.voice)
        self.now += 120
        self.voice.is_obfuscated.return_value = False
        self.generator.channel_visibility_changed(self.voice)
        await self.generator.reconcile()
        self.voice.delete.assert_not_awaited()
        self.now += 61
        await self.generator.reconcile()
        self.voice.delete.assert_awaited_once()
        self.db.delete_generated_channel.assert_awaited_once()

    async def test_obfuscated_trigger_never_clones_or_creates_records(self):
        member, trigger = self.member_and_trigger()
        trigger.is_obfuscated.return_value = True
        trigger.clone = AsyncMock()
        self.settings.type = VoiceGeneratorType.CLONED
        await self.generator.join(member, trigger)
        trigger.clone.assert_not_awaited()
        self.guild.create_voice_channel.assert_not_awaited()
        self.db.get_generated_channel.assert_not_awaited()
        self.db.create_generated_channel.assert_not_awaited()
        member.move_to.assert_not_awaited()

    async def test_trigger_hidden_while_reading_configuration_is_not_cloned(self):
        member, trigger = self.member_and_trigger()
        trigger.clone = AsyncMock()
        self.settings.type = VoiceGeneratorType.CLONED

        async def configuration(*args):
            trigger.is_obfuscated.return_value = True
            return self.settings

        self.db.get_generator.side_effect = configuration
        await self.generator.join(member, trigger)
        trigger.clone.assert_not_awaited()
        self.db.create_generated_channel.assert_not_awaited()
        member.move_to.assert_not_awaited()

    async def test_trigger_hidden_before_creation_task_runs_is_not_cloned(self):
        member, trigger = self.member_and_trigger()
        trigger.clone = AsyncMock()
        self.settings.type = VoiceGeneratorType.CLONED

        async def configuration(*args):
            asyncio.get_running_loop().call_soon(
                setattr, trigger.is_obfuscated, "return_value", True
            )
            return self.settings

        self.db.get_generator.side_effect = configuration
        await self.generator.join(member, trigger)
        trigger.clone.assert_not_awaited()
        self.db.create_generated_channel.assert_not_awaited()
        member.move_to.assert_not_awaited()

    async def test_voice_hidden_during_companion_fetch_does_not_edit_permissions(self):
        member, _ = self.member_and_trigger()
        member.voice.channel = self.voice
        self.db.get_generated_channel.return_value = self.record
        del self.channels[self.text.id]

        async def fetched(*args):
            self.voice.is_obfuscated.return_value = True
            return self.text

        self.guild.fetch_channel.side_effect = fetched
        await self.generator.join(member, self.voice)
        self.text.set_permissions.assert_not_awaited()
        self.guild.create_voice_channel.assert_not_awaited()

    async def test_new_voice_hidden_during_persistence_does_not_create_companion(self):
        member, trigger = self.member_and_trigger()
        self.settings.defaultOptions = [VoiceGeneratorOption.TEXT]

        async def persisted(*args):
            self.voice.is_obfuscated.return_value = True

        self.db.create_generated_channel.side_effect = persisted
        await self.generator.join(member, trigger)
        self.db.create_generated_channel.assert_awaited_once()
        self.guild.create_text_channel.assert_not_awaited()
        self.voice.delete.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
        member.move_to.assert_not_awaited()

    async def test_hidden_text_channel_is_not_edited_on_join_or_leave(self):
        member, _ = self.member_and_trigger()
        member.voice.channel = self.voice
        self.text.is_obfuscated.return_value = True
        self.db.get_generated_channel.return_value = self.record
        await self.generator.join(member, self.voice)
        self.text.set_permissions.assert_not_awaited()
        member.voice = None
        self.voice.voice_states = {99: Mock()}
        await self.generator._leave(member, self.voice, self.record)
        self.text.set_permissions.assert_not_awaited()
        self.db.delete_generated_channel.assert_not_awaited()
