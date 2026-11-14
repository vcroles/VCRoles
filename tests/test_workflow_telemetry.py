import asyncio
import importlib
import inspect
import sys
import time
import unittest
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, Mock

import discord

from tests import test_generator, test_telemetry, test_tts
from utils.logging import audit_event
from utils.telemetry import get_telemetry, observed

voice = importlib.import_module("cogs.voicestate")


class WorkflowTelemetryTests(unittest.IsolatedAsyncioTestCase):
    configured = test_telemetry.TelemetryTests.configured
    metrics = test_telemetry.TelemetryTests.metrics

    def queue(self):
        cog = object.__new__(voice.VoiceState)
        cog.client = Mock(loop=asyncio.get_running_loop())
        cog.client.get_guild.return_value = Mock()
        cog.member_queues = {}
        cog.edit_tasks = set()
        cog.handle_member_edit = AsyncMock()
        return cog, Mock(id=2, guild=Mock(id=1))

    async def test_coalesced_batch_links_sources_and_measures_until_completion(self):
        telemetry = await self.configured()
        cog, member = self.queue()
        sources = []
        for _ in range(2):
            with telemetry.operation("voice_state", "source"):
                sources.append(telemetry.capture_context())
                await cog.queue_member_update(
                    member, [], [], voice.NicknameUpdate("private nickname")
                )
        cog.member_queues[1] = [
            replace(update, enqueued_at=time.monotonic() - 1)
            for update in cog.member_queues[1]
        ]
        entered, release = asyncio.Event(), asyncio.Event()

        async def edit(*args):
            entered.set()
            await release.wait()

        cog.handle_member_edit.side_effect = edit
        with telemetry.operation("command", "ambient_flush"):
            await cog.process_queues()
            tasks = list(cog.edit_tasks)
            await asyncio.wait_for(entered.wait(), 1)
            self.assertFalse(tasks[0].done())
            release.set()
            await asyncio.wait_for(asyncio.gather(*tasks), 1)
        telemetry.traces.force_flush()
        batch = next(
            s
            for s in self.spans.get_finished_spans()
            if s.name == "member_edit.apply_batch"
        )
        self.assertIsNone(batch.parent)
        self.assertEqual(
            {link.context.trace_id for link in batch.links},
            {source.trace_id for source in sources},
        )
        self.assertEqual(len(cog.handle_member_edit.await_args.args[3]), 2)
        self.assertNotIn("private nickname", str(dict(batch.attributes)))
        metrics = self.metrics()
        for name in (
            "vcroles.member_edit.queue_wait",
            "vcroles.member_edit.queue_completion",
        ):
            point = metrics[name].data.data_points[0]
            self.assertEqual(point.count, 2)
            self.assertGreaterEqual(point.sum, 2)
        self.assertEqual(
            metrics["vcroles.member_edit.queue_events"].data.data_points[0].value, 2
        )

    async def test_batch_links_are_bounded_without_losing_update_counts(self):
        telemetry = await self.configured()
        cog, member = self.queue()
        for _ in range(12):
            with telemetry.operation("voice_state", "source"):
                await cog.queue_member_update(
                    member, [], [], voice.NicknameUpdate("private")
                )
        await cog.process_queues()
        await asyncio.gather(*list(cog.edit_tasks))
        telemetry.traces.force_flush()
        batch = next(
            s
            for s in self.spans.get_finished_spans()
            if s.name == "member_edit.apply_batch"
        )
        self.assertEqual(len(batch.links), 8)
        self.assertEqual(batch.attributes["queue.links_dropped"], 4)
        cog.handle_member_edit.assert_awaited_once()
        self.assertEqual(
            self.metrics()["vcroles.member_edit.queue_events"]
            .data.data_points[0]
            .value,
            12,
        )

    async def test_handled_edit_error_marks_batch_as_error(self):
        telemetry = await self.configured()
        cog, member = self.queue()

        async def edit(*args):
            with telemetry.operation("member_edit", "dispatch"):
                telemetry.failure(ValueError("private error text"))

        cog.handle_member_edit.side_effect = edit
        await cog.queue_member_update(member, [], [], voice.NicknameUpdate("private"))
        await cog.process_queues()
        await asyncio.gather(*list(cog.edit_tasks))
        point = self.metrics()["vcroles.member_edit.queue_events"].data.data_points[0]
        self.assertEqual(point.attributes["outcome"], "error")
        telemetry.traces.force_flush()
        self.assertTrue(
            all(
                s.status.status_code.name == "ERROR"
                for s in self.spans.get_finished_spans()
            )
        )

    async def test_cancelled_batch_finishes_metrics_and_releases_task(self):
        await self.configured()
        cog, member = self.queue()
        entered = asyncio.Event()

        async def edit(*args):
            entered.set()
            await asyncio.Event().wait()

        cog.handle_member_edit.side_effect = edit
        await cog.queue_member_update(member, [], [], voice.NicknameUpdate("private"))
        await cog.process_queues()
        task = next(iter(cog.edit_tasks))
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(cog.edit_tasks)
        point = self.metrics()["vcroles.member_edit.queue_events"].data.data_points[0]
        self.assertEqual(point.attributes["outcome"], "cancelled")

    async def test_command_decorator_preserves_schema_result_and_error(self):
        telemetry = await self.configured()

        class Commands:
            @discord.app_commands.command()
            @observed("command")
            async def example(self, interaction: discord.Interaction, value: str):
                if value.startswith("error"):
                    raise ValueError(value)
                return value

        command = Commands.example
        self.assertEqual([p.name for p in command.parameters], ["value"])
        self.assertEqual(
            await command.callback(Commands(), Mock(), "private argument"),
            "private argument",
        )
        with self.assertRaises(ValueError):
            await command.callback(Commands(), Mock(), "error private argument")
        telemetry.traces.force_flush()
        spans = self.spans.get_finished_spans()
        self.assertEqual([s.name for s in spans], ["command.Commands.example"] * 2)
        self.assertNotIn("private argument", str([dict(s.attributes) for s in spans]))
        self.assertEqual(
            {
                p.attributes["outcome"]
                for p in self.metrics()["vcroles.operations"].data.data_points
            },
            {"success", "error"},
        )

    async def test_tts_phases_and_cleanup_share_command_trace_without_text(self):
        telemetry = await self.configured()
        fixture = test_tts.TTSTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addAsyncCleanup(fixture.asyncTearDown)
        task = fixture.start_command()
        await asyncio.wait_for(fixture.started.wait(), 1)
        fixture.complete()
        await asyncio.wait_for(task, 1)
        fixture.voice.disconnect.assert_awaited_once()
        fixture.source.cleanup.assert_called()
        telemetry.traces.force_flush()
        spans = self.spans.get_finished_spans()
        self.assertTrue(
            {
                "command.TTS.play",
                "tts._prepare_play",
                "tts._play",
                "tts.synthesis",
                "tts.voice_connect",
                "tts.playback",
                "tts.cleanup",
            }.issubset({s.name for s in spans})
        )
        self.assertEqual(len({s.context.trace_id for s in spans}), 1)
        self.assertNotIn("Hello", str([dict(s.attributes) for s in spans]))

    async def test_enabled_tts_unload_records_cancellation_after_cleanup(self):
        await self.configured()
        fixture = test_tts.TTSTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.addAsyncCleanup(fixture.asyncTearDown)
        task = fixture.start_command()
        await asyncio.wait_for(fixture.started.wait(), 1)
        await asyncio.wait_for(fixture.cog.cog_unload(), 1)
        await asyncio.wait_for(task, 1)
        fixture.source.cleanup.assert_called()
        fixture.voice.disconnect.assert_awaited_once_with(force=True)
        self.assertFalse(fixture.cog.playback_tasks)
        points = self.metrics()["vcroles.operations"].data.data_points
        self.assertTrue(
            any(
                p.attributes
                == {"component": "tts", "operation": "_play", "outcome": "cancelled"}
                for p in points
            )
        )
        self.assertTrue(
            any(
                p.attributes
                == {"component": "tts", "operation": "cleanup", "outcome": "success"}
                for p in points
            )
        )

    async def test_all_real_command_schemas_are_preserved_by_decorators(self):
        from discord.ext import commands

        root = Path(__file__).resolve().parents[1]
        client = discord.Client(intents=discord.Intents.none())
        tree = discord.app_commands.CommandTree(client)

        def schemas(source, name):
            module = ModuleType(name)
            module.__file__ = name + ".py"
            sys.modules[name] = module
            try:
                exec(compile(source, module.__file__, "exec"), module.__dict__)  # noqa: S102 - compare trusted local command definitions
                result = {}
                for value in vars(module).values():
                    if (
                        inspect.isclass(value)
                        and issubclass(value, commands.Cog)
                        and value.__module__ == name
                    ):
                        for command in value.__cog_app_commands__:
                            result[f"app:{value.__name__}:{command.name}"] = (
                                command.to_dict(tree)
                            )
                        for command in value.__cog_commands__:
                            result[
                                f"prefix:{value.__name__}:{command.qualified_name}"
                            ] = str(inspect.signature(inspect.unwrap(command.callback)))
                return result
            finally:
                sys.modules.pop(name, None)

        count = 0
        try:
            for path in (root / "cogs").glob("*.py"):
                current = path.read_text()
                if '@observed("command")' not in current:
                    continue
                previous = "\n".join(
                    line
                    for line in current.splitlines()
                    if line.strip() != '@observed("command")'
                )
                name = "cogs._schema_" + path.stem.replace("-", "_")
                self.assertEqual(
                    schemas(previous, name), schemas(current, name), path.name
                )
                count += 1
            self.assertGreater(count, 0)
        finally:
            await client.close()

    async def test_generator_cleanup_remains_nested_and_audit_failure_counts(self):
        telemetry = await self.configured()
        fixture = test_generator.GeneratorTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        with telemetry.operation("voice_state", "source"):
            await fixture.generator._cleanup(fixture.voice, fixture.text)
        fixture.voice.delete.assert_awaited_once()
        telemetry.traces.force_flush()
        spans = self.spans.get_finished_spans()
        self.assertEqual(len({s.context.trace_id for s in spans}), 1)
        self.assertIn("generator._cleanup", {s.name for s in spans})
        with telemetry.operation("generator", "audit_probe"):
            audit_event(
                "generator_record_delete_failed",
                error=ValueError("private"),
                operation_id="a" * 32,
                guild_id=123,
            )
        telemetry.logs.force_flush()
        record = self.logs.get_finished_logs()[0].log_record
        self.assertEqual(record.attributes["operation_id"], "a" * 32)
        self.assertNotIn("guild_id", record.attributes)
        self.assertEqual(
            self.metrics()["vcroles.generator.events"].data.data_points[0].value, 1
        )

    async def test_finished_parent_is_not_mutated_by_late_child_failure(self):
        telemetry = await self.configured()
        release = asyncio.Event()

        async def late_child():
            await release.wait()
            get_telemetry().failure(ValueError("late"))

        with telemetry.operation("command", "parent") as state:
            task = asyncio.create_task(late_child())
        release.set()
        await task
        self.assertEqual(state.outcome, "success")

    async def test_voice_event_failure_log_retains_its_source_trace(self):
        from functools import partial
        from types import SimpleNamespace

        from utils.client import VCRolesClient
        from utils.types import LogLevel

        telemetry = await self.configured()
        cog, member = self.queue()
        cog.unloading = False
        cog.event_tasks = set()
        cog.client.log = partial(
            VCRolesClient.log, SimpleNamespace(console_log_level=LogLevel.ERROR)
        )

        @observed("voice_state")
        async def failing_handler(*args):
            raise ValueError("private content")

        cog.handle_voice_state_update = failing_handler
        await cog.on_voice_state_update(
            member, SimpleNamespace(channel=None), SimpleNamespace(channel=None)
        )
        self.assertFalse(cog.event_tasks)
        telemetry.traces.force_flush()
        telemetry.logs.force_flush()
        span = next(
            s
            for s in self.spans.get_finished_spans()
            if s.name == "voice_state.on_voice_state_update"
        )
        record = self.logs.get_finished_logs()[0].log_record
        self.assertEqual(record.trace_id, span.context.trace_id)
        self.assertEqual(span.status.status_code.name, "ERROR")


if __name__ == "__main__":
    unittest.main()
