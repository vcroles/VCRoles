import asyncio
import json
import logging
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from utils.logging import JSONFormatter
from utils.telemetry import Telemetry, _endpoint, observed


class TelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def configured(self, span_exporter=None):
        self.spans = span_exporter or InMemorySpanExporter()
        self.logs = InMemoryLogRecordExporter()
        self.reader = InMemoryMetricReader()
        with (
            patch.dict(
                "os.environ",
                {
                    "VCROLES_OTEL_ENABLED": "1",
                    "OTEL_EXPORTER_OTLP_ENDPOINT": "http://localhost:4318",
                    "VCROLES_OTEL_USERNAME": "vcroles",
                    "VCROLES_OTEL_PASSWORD": "test-only-password-" * 3,
                    "HTTP_PROXY": "http://127.0.0.1:1",
                    "HTTPS_PROXY": "http://127.0.0.1:1",
                },
                clear=True,
            ),
            patch("utils.logging.source_revision", return_value="test-revision"),
            patch(
                "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
                return_value=self.spans,
            ),
            patch(
                "opentelemetry.exporter.otlp.proto.http._log_exporter.OTLPLogExporter",
                return_value=self.logs,
            ),
            patch(
                "opentelemetry.sdk.metrics.export.PeriodicExportingMetricReader",
                return_value=self.reader,
            ),
        ):
            telemetry = Telemetry.from_environment()
        self.assertTrue(telemetry.enabled)
        self.addAsyncCleanup(telemetry.close)
        active = patch("utils.telemetry._active", telemetry)
        active.start()
        self.addCleanup(active.stop)
        return telemetry

    def metrics(self):
        return {
            metric.name: metric
            for resource in self.reader.get_metrics_data().resource_metrics
            for scope in resource.scope_metrics
            for metric in scope.metrics
        }

    async def test_disabled_mode_has_no_providers_or_runtime_tasks(self):
        with patch.dict("os.environ", {}, clear=True):
            telemetry = Telemetry.from_environment()
        self.assertFalse(telemetry.enabled)
        self.assertFalse(telemetry.providers)
        telemetry.start_runtime(Mock())
        self.assertIsNone(telemetry.runtime_task)
        with telemetry.operation("database", "get_guild_data"):
            pass
        await telemetry.close()

    async def test_invalid_configuration_fails_open_without_logging_secrets(self):
        secret = "private-password-sentinel"
        with (
            patch.dict(
                "os.environ",
                {
                    "VCROLES_OTEL_ENABLED": "1",
                    "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://user:{secret}@localhost:4318",
                },
                clear=True,
            ),
            self.assertLogs("utils.telemetry", level="WARNING") as captured,
        ):
            telemetry = Telemetry.from_environment()
        self.assertFalse(telemetry.enabled)
        self.assertNotIn(secret, str(captured.output))
        await telemetry.close()

    def test_plain_http_rejects_public_and_credential_bearing_endpoints(self):
        for endpoint in (
            "http://example.com",
            "http://8.8.8.8",
            "http://user:secret@localhost",
            "http://localhost/?token=secret",
        ):
            with self.assertRaises(ValueError):
                _endpoint(endpoint)
        self.assertEqual(
            _endpoint("http://vcroles-collector:4318/"), "http://vcroles-collector:4318"
        )

    async def test_operations_preserve_errors_cancellation_and_privacy(self):
        telemetry = await self.configured()
        sentinel = "query-and-user-content-must-stay-local"

        @observed("database")
        async def lookup(argument):
            error = ValueError(argument)
            try:
                raise error
            except ValueError:
                logging.getLogger("internal.bot").exception(
                    sentinel,
                    extra={
                        "event": "database_lookup_failed",
                        "context": {
                            "status": 503,
                            "sql": sentinel,
                            "member_id": sentinel,
                        },
                    },
                )
                raise

        with self.assertRaises(ValueError) as captured:
            await lookup(sentinel)
        self.assertEqual(str(captured.exception), sentinel)
        with (
            self.assertRaises(asyncio.CancelledError),
            telemetry.operation("database", "cancelled_lookup"),
        ):
            raise asyncio.CancelledError
        telemetry.traces.force_flush()
        telemetry.logs.force_flush()
        spans = self.spans.get_finished_spans()
        self.assertEqual(
            [s.name for s in spans], ["database.lookup", "database.cancelled_lookup"]
        )
        self.assertFalse(any(s.events for s in spans))
        self.assertNotIn(sentinel, str([dict(s.attributes) for s in spans]))
        self.assertEqual(spans[0].attributes["error.type"], "ValueError")
        self.assertEqual(spans[0].status.status_code.name, "ERROR")
        records = self.logs.get_finished_logs()
        self.assertEqual(len(records), 1)
        record = records[0].log_record
        self.assertEqual(record.body, "database_lookup_failed")
        self.assertEqual(record.severity_text, "ERROR")
        self.assertEqual(record.severity_number.value, 17)
        self.assertEqual(record.trace_id, spans[0].context.trace_id)
        self.assertNotIn(sentinel, str(record.attributes))
        points = self.metrics()["vcroles.operations"].data.data_points
        self.assertEqual(
            {p.attributes["outcome"] for p in points}, {"error", "cancelled"}
        )
        self.assertTrue(
            all(
                set(p.attributes) == {"component", "operation", "outcome"}
                for p in points
            )
        )
        self.assertEqual(
            set(telemetry.resource.attributes),
            {
                "service.name",
                "service.version",
                "service.instance.id",
                "deployment.environment.name",
            },
        )

    async def test_telemetry_failure_does_not_change_operation_result(self):
        telemetry = await self.configured()
        body = AsyncMock(return_value="result")
        decorated = observed("database")(body)
        with (
            patch.object(
                telemetry.tracer, "start_as_current_span", side_effect=RuntimeError
            ),
            patch.object(telemetry.operations, "add", side_effect=RuntimeError),
            self.assertLogs("utils.telemetry", level="WARNING"),
        ):
            self.assertEqual(await decorated(), "result")
        body.assert_awaited_once()

    async def test_database_cache_hits_are_measured_without_extra_queries(self):
        from utils.database import DatabaseUtils

        telemetry = await self.configured()
        database = DatabaseUtils()
        database.guild_cache.clear()
        self.addCleanup(database.guild_cache.clear)
        record = SimpleNamespace(id="123")
        database.db = Mock(guild=Mock(find_unique=AsyncMock(return_value=record)))
        self.assertIs(await database.get_guild_data(123), record)
        self.assertIs(await database.get_guild_data(123), record)
        database.db.guild.find_unique.assert_awaited_once()
        telemetry.traces.force_flush()
        self.assertEqual(len(self.spans.get_finished_spans()), 2)
        self.assertNotIn(
            "123", str([dict(s.attributes) for s in self.spans.get_finished_spans()])
        )

    async def test_local_json_logs_include_active_trace_context(self):
        telemetry = await self.configured()
        record = logging.makeLogRecord(
            {
                "msg": "local message",
                "run_id": "test",
                "revision": "test",
                "context": {},
            }
        )
        with telemetry.operation("database", "get_generator"):
            result = json.loads(JSONFormatter().format(record))
        telemetry.traces.force_flush()
        span = self.spans.get_finished_spans()[0]
        self.assertEqual(result["trace_id"], f"{span.context.trace_id:032x}")
        self.assertEqual(result["span_id"], f"{span.context.span_id:016x}")
        self.assertNotIn("trace_id", json.loads(JSONFormatter().format(record)))

    async def test_runtime_and_shard_health_have_bounded_labels(self):
        telemetry = await self.configured()
        client = Mock()
        client.is_ready.return_value = False
        client.db.db.is_connected.return_value = True
        client.guilds = [Mock()]
        client.shards = {
            0: SimpleNamespace(latency=0.125),
            1: SimpleNamespace(latency=float("inf")),
        }
        telemetry._sample_runtime(client, 0.01)
        telemetry.gateway("ready", 0)
        telemetry.gateway("disconnected", 0)
        telemetry.health(503)
        metrics = self.metrics()
        self.assertEqual(metrics["vcroles.bot.ready"].data.data_points[0].value, 0)
        self.assertEqual(
            metrics["vcroles.database.connected"].data.data_points[0].value, 1
        )
        self.assertEqual(
            metrics["vcroles.gateway.connected"].data.data_points[0].value, 0
        )
        self.assertEqual(len(metrics["vcroles.gateway.latency"].data.data_points), 1)
        telemetry.start_runtime(client)
        task = telemetry.runtime_task
        telemetry.start_runtime(client)
        self.assertIs(telemetry.runtime_task, task)
        await telemetry.close()
        self.assertTrue(task.done())

    async def test_gateway_callback_correlates_its_log_and_keeps_database_open(self):
        import discord

        from utils.client import VCRolesClient
        from utils.types import LogLevel

        telemetry = await self.configured()
        database = Mock(disconnect=AsyncMock())
        client = VCRolesClient(Mock(), database, discord.Intents.none(), LogLevel.ERROR)
        try:
            await client.on_shard_disconnect(3)
            telemetry.traces.force_flush()
            telemetry.logs.force_flush()
            span = self.spans.get_finished_spans()[0]
            record = self.logs.get_finished_logs()[0].log_record
            self.assertEqual(span.name, "gateway.on_shard_disconnect")
            self.assertEqual(record.body, "shard_disconnected")
            self.assertEqual(record.trace_id, span.context.trace_id)
            self.assertEqual(record.attributes["shard_id"], 3)
            database.disconnect.assert_not_awaited()
        finally:
            await client.http.close()

    async def test_trace_context_failure_does_not_break_local_log_formatting(self):
        await self.configured()
        record = logging.makeLogRecord(
            {"msg": "persist me", "run_id": "test", "revision": "test", "context": {}}
        )
        with patch("opentelemetry.trace.get_current_span", side_effect=RuntimeError):
            result = json.loads(JSONFormatter().format(record))
        self.assertEqual(result["message"], "persist me")
        self.assertNotIn("trace_id", result)

    async def test_shutdown_budget_does_not_block_event_loop(self):
        telemetry = Telemetry()
        entered, release = threading.Event(), threading.Event()

        def slow_shutdown():
            entered.set()
            release.wait(2)

        provider = Mock(shutdown=Mock(side_effect=slow_shutdown))
        telemetry.providers = [provider]
        telemetry.SHUTDOWN_TIMEOUT = 0.05
        ticks = 0

        async def heartbeat():
            nonlocal ticks
            for _ in range(8):
                ticks += 1
                await asyncio.sleep(0.01)

        try:
            with self.assertLogs("utils.telemetry", level="WARNING"):
                start = time.monotonic()
                await asyncio.gather(telemetry.close(), telemetry.close(), heartbeat())
                self.assertLess(time.monotonic() - start, 0.5)
            self.assertTrue(entered.is_set())
            self.assertEqual(ticks, 8)
            provider.shutdown.assert_called_once()
        finally:
            release.set()
            telemetry.shutdown_thread.join(2)

    async def test_full_export_queue_drops_telemetry_without_blocking_operations(self):
        class BlockedExporter(InMemorySpanExporter):
            def __init__(self):
                super().__init__()
                self.entered = threading.Event()
                self.release = threading.Event()

            def export(self, spans):
                self.entered.set()
                self.release.wait(5)
                return super().export(spans)

        exporter = BlockedExporter()
        telemetry = await self.configured(exporter)
        count = 1400
        try:
            for _ in range(128):
                with telemetry.operation("database", "lookup"):
                    pass
            deadline = time.monotonic() + 2
            while not exporter.entered.is_set() and time.monotonic() < deadline:
                await asyncio.sleep(0.01)
            self.assertTrue(exporter.entered.is_set())
            with self.assertLogs("opentelemetry.sdk", level="WARNING"):
                start = time.monotonic()
                for _ in range(count):
                    with telemetry.operation("database", "lookup"):
                        pass
                self.assertLess(time.monotonic() - start, 1)
        finally:
            exporter.release.set()
        telemetry.traces.force_flush()
        exported = len(exporter.get_finished_spans())
        self.assertLess(exported, count + 128)
        self.assertLessEqual(exported, 1024 + 128)
        dropped = [
            p.value
            for p in self.metrics()[
                "otel.sdk.processor.span.processed"
            ].data.data_points
            if p.attributes.get("error.type") == "queue_full"
        ]
        self.assertGreater(sum(dropped), 0)

    async def test_real_http_exporter_outage_keeps_loop_responsive_and_closes(self):
        received = threading.Event()

        class UnavailableCollector(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                self.send_response(503)
                self.send_header("Content-Length", "0")
                self.end_headers()
                received.set()

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), UnavailableCollector)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(
                "os.environ",
                {
                    "VCROLES_OTEL_ENABLED": "1",
                    "OTEL_EXPORTER_OTLP_ENDPOINT": f"http://127.0.0.1:{server.server_port}",
                    "VCROLES_OTEL_USERNAME": "vcroles",
                    "VCROLES_OTEL_PASSWORD": "test-only-password-" * 3,
                    "HTTP_PROXY": "http://127.0.0.1:1",
                    "HTTPS_PROXY": "http://127.0.0.1:1",
                },
                clear=True,
            ):
                telemetry = Telemetry.from_environment()
            self.assertTrue(telemetry.enabled)
            try:
                with telemetry.operation("database", "lookup"):
                    pass
                deadline = time.monotonic() + 3
                while not received.is_set() and time.monotonic() < deadline:
                    await asyncio.sleep(0.01)
                self.assertTrue(received.is_set())
                start = time.monotonic()
                await asyncio.sleep(0.025)
                self.assertLess(time.monotonic() - start, 0.25)
            finally:
                start = time.monotonic()
                await telemetry.close()
                self.assertLess(time.monotonic() - start, 5.5)
                self.assertFalse(telemetry.shutdown_thread.is_alive())
        finally:
            await asyncio.to_thread(server.shutdown)
            server.server_close()
            thread.join(2)


if __name__ == "__main__":
    unittest.main()
