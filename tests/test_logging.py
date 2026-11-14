import asyncio
import io
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import discord

from cogs.status import Status
from utils.client import VCRolesClient
from utils.logging import (
    AUDIT_LOGGER,
    PersistentFileHandler,
    audit_event,
    log_paths,
    setup_logging,
)
from utils.types import LogLevel
from voicestate.generator import Generator


class PersistentLoggingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = logging.getLogger()
        names = (
            "",
            "vcroles.audit",
            "internal.bot",
            "discord.voice_client",
            "discord.player",
            "aiohttp",
            "httpx",
            "gtts",
        )
        self.states = []
        for name in names:
            logger = logging.getLogger(name)
            self.states.append(
                (logger, logger.level, list(logger.handlers), logger.propagate)
            )
            logger.handlers = []
        self.hooks = (sys.excepthook, threading.excepthook)
        self.addCleanup(self.restore_logging)
        self.stderr = io.StringIO()
        redirect = patch("sys.stderr", self.stderr)
        redirect.start()
        self.addCleanup(redirect.stop)
        revision = patch("utils.logging.source_revision", return_value="test-revision")
        revision.start()
        self.addCleanup(revision.stop)
        setup_logging(self.directory.name)
        self.main_path, self.audit_path = log_paths(self.directory.name)

    def restore_logging(self):
        for logger, level, handlers, propagate in self.states:
            for handler in logger.handlers:
                if handler not in handlers:
                    handler.close()
            logger.handlers = handlers
            logger.setLevel(level)
            logger.propagate = propagate
        sys.excepthook, threading.excepthook = self.hooks

    def records(self, path=None):
        return [
            json.loads(line)
            for line in (path or self.main_path).read_text().splitlines()
        ]

    def test_client_logs_are_immediate_and_preserve_traceback_and_context(self):
        client = object.__new__(VCRolesClient)
        client.console_log_level = LogLevel.ERROR
        with patch("utils.logging.os.fsync", wraps=os.fsync) as sync:
            try:
                raise RuntimeError("simulated failure")
            except RuntimeError:
                client.log(
                    LogLevel.ERROR,
                    "Member update failed",
                    event="member_update_failed",
                    guild_id=123,
                    member_id=456,
                    shard_id=2,
                )
            self.assertEqual(sync.call_count, 1)
        record = self.records()[-1]
        self.assertEqual(record["event"], "member_update_failed")
        self.assertEqual(
            record["context"], {"guild_id": 123, "member_id": 456, "shard_id": 2}
        )
        self.assertIn("raise RuntimeError", record["exception"]["traceback"])
        self.assertEqual(record["revision"], "test-revision")
        self.assertTrue(record["run_id"])
        self.assertTrue(record["timestamp"].endswith("+00:00"))
        self.assertFalse(hasattr(client, "log_queue"))

    def test_debug_logs_are_persisted_without_console_noise(self):
        client = object.__new__(VCRolesClient)
        client.console_log_level = LogLevel.ERROR
        client.log(LogLevel.DEBUG, "debug diagnostic")
        self.assertEqual(self.records()[-1]["message"], "debug diagnostic")
        self.assertNotIn("debug diagnostic", self.stderr.getvalue())

    def test_audit_records_sync_before_return_and_share_run_metadata(self):
        with patch("utils.logging.os.fsync", wraps=os.fsync) as sync:
            audit_event(
                "generator_channel_delete_requested",
                channel_id=123,
                operation_id="operation",
            )
            self.assertEqual(sync.call_count, 1)
        audit = self.records(self.audit_path)[-1]
        combined = self.records()[-1]
        self.assertEqual(audit["context"]["operation_id"], "operation")
        self.assertEqual(audit, combined)

    def test_audit_sync_failure_prevents_discord_deletion(self):
        guild = Mock(id=1, shard_id=0, unavailable=False)
        voice = Mock(spec=discord.VoiceChannel, id=10, guild=guild)
        voice.voice_states = {}
        voice.delete = AsyncMock()
        client = Mock()
        client.is_ready.return_value = True
        client.get_shard.return_value.is_closed.return_value = False
        client.db.delete_generated_channel = AsyncMock()
        generator = Generator(client)
        with patch("utils.logging.os.fsync", side_effect=OSError("disk unavailable")):
            with self.assertRaisesRegex(OSError, "Could not persist audit log"):
                asyncio.run(generator._cleanup(voice, None))
        voice.delete.assert_not_awaited()
        client.db.delete_generated_channel.assert_not_awaited()

    def test_json_keeps_multiline_messages_and_tracebacks_in_one_record(self):
        try:
            raise ValueError("first\nsecond")
        except ValueError:
            logging.getLogger("test").exception("message\nwith newline")
        record = self.records()[-1]
        self.assertEqual(record["message"], "message\nwith newline")
        self.assertEqual(record["exception"]["type"], "ValueError")

    def test_rotation_is_bounded_for_main_and_audit_logs(self):
        setup_logging(
            self.directory.name, max_bytes=1024, audit_max_bytes=1024, backups=2
        )
        for index in range(12):
            audit_event("rotation_test", index=index)
        for path in (self.main_path, self.audit_path):
            backups = list(path.parent.glob(path.name + ".*"))
            self.assertEqual(len(backups), 2)
            records = self.records(path)
            self.assertEqual(records[-1]["context"]["index"], 11)
            for backup in backups:
                self.assertTrue(self.records(backup))

    def test_reinitialization_keeps_history_without_duplicate_handlers(self):
        logging.getLogger("test").info("before reinitialization")
        setup_logging(self.directory.name)
        logging.getLogger("test").info("after reinitialization")
        messages = [record["message"] for record in self.records()]
        self.assertEqual(messages.count("before reinitialization"), 1)
        self.assertEqual(messages.count("after reinitialization"), 1)
        self.assertEqual(len(self.root.handlers), 2)
        self.assertEqual(len(AUDIT_LOGGER.handlers), 1)

    def test_partial_crash_record_does_not_corrupt_next_run(self):
        self.main_path.write_text('{"partial":')
        setup_logging(self.directory.name)
        lines = self.main_path.read_text().splitlines()
        self.assertEqual(lines[0], '{"partial":')
        self.assertEqual(json.loads(lines[1])["event"], "logging_initialized")

    def test_open_failure_is_not_silently_replaced_with_stdout(self):
        blocked = Path(self.directory.name) / "not-a-directory"
        blocked.write_text("file")
        with self.assertRaises(OSError):
            setup_logging(blocked)
        logging.getLogger("test").info("previous handlers remain usable")
        self.assertEqual(
            self.records()[-1]["message"], "previous handlers remain usable"
        )

    def test_runtime_main_file_failure_reports_to_stderr(self):
        handler = next(
            h for h in self.root.handlers if isinstance(h, PersistentFileHandler)
        )
        handler.maxBytes = 1
        with patch.object(handler, "doRollover", side_effect=OSError("disk full")):
            logging.getLogger("test").error("write failed")
        self.assertIn("Persistent log write failed", self.stderr.getvalue())

    def test_unhandled_thread_exception_is_persisted(self):
        def failed():
            raise RuntimeError("thread failure")

        thread = threading.Thread(target=failed, name="test-worker")
        thread.start()
        thread.join(timeout=2)
        record = self.records()[-1]
        self.assertEqual(record["event"], "unhandled_thread_exception")
        self.assertEqual(record["context"]["thread"], "test-worker")
        self.assertIn("thread failure", record["exception"]["traceback"])

    def test_health_logs_initial_status_and_transitions_without_poll_spam(self):
        client = Mock()
        client.is_ready.side_effect = [False, False, True, True, False]

        async def poll():
            cog = Status(client)
            handler = next(iter(cog.app.router.routes())).handler
            return [(await handler(Mock())).status for _ in range(5)]

        self.assertEqual(asyncio.run(poll()), [503, 503, 200, 200, 503])
        records = [r for r in self.records() if r["event"] == "health_status_changed"]
        self.assertEqual([r["context"]["status"] for r in records], [503, 200, 503])
        self.assertEqual(
            [r["context"]["previous_status"] for r in records], [None, 503, 200]
        )

    def test_logs_survive_hard_exit_and_subsequent_restart(self):
        script = """import logging, os, sys
from utils.logging import setup_logging, audit_event
setup_logging(sys.argv[1])
logging.getLogger('test').info('last message before exit')
audit_event('audit_before_exit', channel_id=123)
os._exit(7)
"""
        for _ in range(2):
            result = subprocess.run(
                [sys.executable, "-c", script, self.directory.name],
                cwd=Path(__file__).resolve().parents[1],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            self.assertEqual(result.returncode, 7)
        records = [
            r for r in self.records() if r["message"] == "last message before exit"
        ]
        self.assertEqual(len(records), 2)
        self.assertEqual(len({r["run_id"] for r in records}), 2)
        self.assertEqual(len(self.records(self.audit_path)), 2)
