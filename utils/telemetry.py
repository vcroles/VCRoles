"""Optional, bounded OTLP export. Business operations never depend on delivery."""

from __future__ import annotations

import asyncio
import base64
import functools
import ipaddress
import logging
import math
import os
import re
import resource
import sys
import threading
import time
from contextlib import contextmanager
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)
_IDENTIFIER = re.compile(r"[a-zA-Z0-9_.-]{1,128}\Z")
_LOG_FIELDS = {
    "shard_id",
    "closing",
    "database_connected",
    "status",
    "previous_status",
    "guild_count",
    "shard_count",
    "event_tasks",
    "edit_tasks",
    "count",
}
_METRIC_FIELDS = {
    "component",
    "operation",
    "outcome",
    "event",
    "shard_id",
    "status",
    "otel.component.type",
    "otel.signal",
    "reason",
    "error.type",
}


def _identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError("Invalid telemetry identifier")
    return value


def _endpoint(value: str) -> str:
    url = urlsplit(value)
    if (
        url.scheme not in {"http", "https"}
        or not url.hostname
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
    ):
        raise ValueError("Invalid OTLP endpoint")
    # Plain HTTP is restricted to local Docker names and private IPs. Remote
    # DNS endpoints require TLS; credentials never belong in the URL.
    if url.scheme == "http":
        host = url.hostname
        if host not in {"localhost", "vcroles-collector"}:
            address = ipaddress.ip_address(host)
            if not (
                address.is_loopback
                or address.is_private
                or address in ipaddress.ip_network("100.64.0.0/10")
            ):
                raise ValueError("Plain HTTP requires a private OTLP endpoint")
    # Validate malformed ports without including the URL in diagnostics.
    _ = url.port
    return value.rstrip("/")


class EventLogHandler(logging.Handler):
    """Export an allowlisted event record, never the original message/exception."""

    def __init__(self, otel_logger):
        super().__init__(logging.INFO)
        self.otel_logger = otel_logger

    def emit(self, record):
        event = getattr(record, "event", None)
        if not isinstance(event, str) or not _IDENTIFIER.fullmatch(event):
            return
        if record.name not in {
            "utils.client",
            "cogs.status",
            "internal.bot",
            "vcroles.audit",
        }:
            return
        try:
            from opentelemetry._logs import LogRecord, SeverityNumber

            attributes = {"event.name": event, "logger.name": record.name}
            context = getattr(record, "context", {})
            for key in _LOG_FIELDS:
                value = context.get(key)
                if isinstance(value, (bool, int)):
                    attributes[key] = value
            if record.exc_info and record.exc_info[1] is not None:
                name = type(record.exc_info[1]).__name__
                attributes["error.type"] = name[:128]
            severity = min(24, max(1, record.levelno // 10 * 4 + 1))
            self.otel_logger.emit(
                LogRecord(
                    timestamp=int(record.created * 1e9),
                    severity_number=SeverityNumber(severity),
                    severity_text=record.levelname,
                    body=event,
                    attributes=attributes,
                )
            )
        except Exception:  # noqa: BLE001, S110 - telemetry must not break audit logging
            # Logging cannot recurse or change a generator audit decision.
            pass


class QueueWarningFilter(logging.Filter):
    """Keep queue overflow from turning each dropped span into a disk write."""

    def __init__(self):
        super().__init__()
        self.last_warning = {}

    def filter(self, record):
        if not record.getMessage().startswith("Queue full, dropping"):
            return True
        now = time.monotonic()
        key = record.getMessage()
        if now - self.last_warning.get(key, float("-inf")) < 30:
            return False
        self.last_warning[key] = now
        return True


class Telemetry:
    SHUTDOWN_TIMEOUT = 5

    def __init__(self):
        self.enabled = False
        self.providers = []
        self.runtime_task = None
        self.shutdown_task = None
        self.shutdown_thread = None
        self.handler = None
        self.queue_warning_filter = None
        self._reported_failure = False

    @classmethod
    def from_environment(cls):
        result = cls()
        if os.environ.get("VCROLES_OTEL_ENABLED", "0") != "1":
            return result
        try:
            result._configure()
            result.enabled = True
            logger.info(
                "OpenTelemetry enabled (bounded export, structured events only)"
            )
        except Exception as error:  # noqa: BLE001 - startup remains usable without telemetry
            # Avoid printing URLs or exception text, which can contain secrets.
            logger.warning(
                "OpenTelemetry disabled: configuration failed (%s)",
                type(error).__name__,
            )
            result._start_provider_shutdown()
        return result

    def _configure(self):
        import requests
        from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk._logs import LoggerProvider
        from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.metrics.view import View
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import SpanLimits, TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON

        from utils.logging import RUN_ID, source_revision

        endpoint = _endpoint(os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"])
        user = _identifier(os.environ["VCROLES_OTEL_USERNAME"])
        password = os.environ["VCROLES_OTEL_PASSWORD"]
        if len(password) < 32:
            raise ValueError("Use a generated collector password")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        options = {
            "headers": {"Authorization": f"Basic {token}"},
            "timeout": 2,
            "max_request_size": 1024 * 1024,
        }

        def exporter(exporter_class, signal, **kwargs):
            # Private collector traffic must not inherit HTTP_PROXY or .netrc
            # from a hosting environment. Each worker owns its own session.
            session = requests.Session()
            session.trust_env = False
            try:
                return exporter_class(
                    endpoint=f"{endpoint}/v1/{signal}",
                    session=session,
                    **options,
                    **kwargs,
                )
            except Exception:
                session.close()
                raise

        # Explicit resources exclude host names, environment-variable resource
        # injection, command lines, and platform/cloud resource detectors.
        self.resource = Resource(
            {
                "service.name": _identifier(
                    os.environ.get("OTEL_SERVICE_NAME", "vcroles")
                ),
                "service.version": source_revision(),
                "service.instance.id": RUN_ID,
                "deployment.environment.name": _identifier(
                    os.environ.get("VCROLES_OTEL_ENVIRONMENT", "development")
                ),
            }
        )
        os.environ.setdefault("OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED", "true")
        reader = PeriodicExportingMetricReader(
            exporter(OTLPMetricExporter, "metrics"),
            export_interval_millis=15000,
            export_timeout_millis=2500,
        )
        self.meters = MeterProvider(
            metric_readers=[reader],
            resource=self.resource,
            shutdown_on_exit=False,
            views=[
                View(
                    instrument_name="*",
                    attribute_keys=_METRIC_FIELDS,
                    aggregation_cardinality_limit=2048,
                )
            ],
        )
        self.providers.append(self.meters)
        self.traces = TracerProvider(
            resource=self.resource,
            shutdown_on_exit=False,
            sampler=ALWAYS_ON,
            span_limits=SpanLimits(
                max_attributes=24, max_events=0, max_links=8, max_attribute_length=128
            ),
        )
        self.providers.append(self.traces)
        self.traces.add_span_processor(
            BatchSpanProcessor(
                exporter(
                    OTLPSpanExporter,
                    "traces",
                    meter_provider=self.meters,
                ),
                max_queue_size=1024,
                max_export_batch_size=128,
                schedule_delay_millis=1000,
                meter_provider=self.meters,
            )
        )
        self.tracer = self.traces.get_tracer("vcroles")
        self.logs = LoggerProvider(resource=self.resource, shutdown_on_exit=False)
        self.providers.append(self.logs)
        self.logs.add_log_record_processor(
            BatchLogRecordProcessor(
                exporter(
                    OTLPLogExporter,
                    "logs",
                    meter_provider=self.meters,
                ),
                max_queue_size=512,
                max_export_batch_size=64,
                schedule_delay_millis=1000,
                meter_provider=self.meters,
            )
        )
        meter = self.meters.get_meter("vcroles")
        self.operations = meter.create_counter("vcroles.operations", unit="{operation}")
        self.duration = meter.create_histogram(
            "vcroles.operation.duration",
            unit="s",
            explicit_bucket_boundaries_advisory=[
                0.001,
                0.005,
                0.01,
                0.05,
                0.1,
                0.5,
                1,
                5,
                15,
                30,
                60,
            ],
        )
        self.gateway_events = meter.create_counter(
            "vcroles.gateway.events", unit="{event}"
        )
        self.shard_connected = meter.create_gauge("vcroles.gateway.connected", unit="1")
        self.health_requests = meter.create_counter(
            "vcroles.health.requests", unit="{request}"
        )
        self.gauges = {
            name: meter.create_gauge(f"vcroles.{name}", unit=unit)
            for name, unit in {
                "bot.ready": "1",
                "database.connected": "1",
                "event_loop.lag": "s",
                "runtime.tasks": "{task}",
                "runtime.guilds": "{guild}",
                "process.peak_rss": "By",
                "gateway.latency": "s",
            }.items()
        }
        self.handler = EventLogHandler(self.logs.get_logger("vcroles.events"))
        logging.getLogger().addHandler(self.handler)
        self.queue_warning_filter = QueueWarningFilter()
        logging.getLogger("opentelemetry.sdk._shared_internal").addFilter(
            self.queue_warning_filter
        )

    def _attempt(self, action, *args, **kwargs):
        try:
            return action(*args, **kwargs)
        except Exception:  # noqa: BLE001 - isolate SDK failures from business operations
            if not self._reported_failure:
                self._reported_failure = True
                logger.warning("Telemetry recording failed; application work continues")
            return None

    @contextmanager
    def operation(self, component, operation):
        if not self.enabled:
            yield
            return
        from opentelemetry.trace import StatusCode

        attributes = {"component": component, "operation": operation}
        start = time.monotonic()
        manager = self._attempt(
            self.tracer.start_as_current_span,
            f"{component}.{operation}",
            attributes=attributes,
            record_exception=False,
            set_status_on_exception=False,
        )
        span = self._attempt(manager.__enter__) if manager is not None else None
        outcome = "success"
        try:
            yield
        except BaseException as error:
            outcome = (
                "cancelled" if isinstance(error, asyncio.CancelledError) else "error"
            )
            if span is not None:
                self._attempt(
                    span.set_attribute, "error.type", type(error).__name__[:128]
                )
                if outcome == "error":
                    self._attempt(span.set_status, StatusCode.ERROR)
            raise
        finally:
            labels = {**attributes, "outcome": outcome}
            self._attempt(self.operations.add, 1, labels)
            self._attempt(self.duration.record, time.monotonic() - start, labels)
            if span is not None:
                self._attempt(manager.__exit__, None, None, None)

    def gateway(self, event, shard_id):
        if self.enabled:
            labels = {"event": event, "shard_id": shard_id}
            self._attempt(self.gateway_events.add, 1, labels)
            self._attempt(
                self.shard_connected.set,
                int(event != "disconnected"),
                {"shard_id": shard_id},
            )

    def health(self, status):
        if self.enabled:
            self._attempt(self.health_requests.add, 1, {"status": status})

    def start_runtime(self, client):
        if self.enabled and self.runtime_task is None:
            self.runtime_task = asyncio.create_task(
                self._monitor(client), name="vcroles-telemetry-runtime"
            )

    async def _monitor(self, client):
        target = time.monotonic()
        while True:
            lag = max(0, time.monotonic() - target)
            self._attempt(self._sample_runtime, client, lag)
            target = time.monotonic() + 5
            await asyncio.sleep(5)

    def _sample_runtime(self, client, lag):
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        for name, value in {
            "bot.ready": int(client.is_ready()),
            "database.connected": int(client.db.db.is_connected()),
            "event_loop.lag": lag,
            "runtime.tasks": len(asyncio.all_tasks()),
            "runtime.guilds": len(client.guilds),
            "process.peak_rss": rss if sys.platform == "darwin" else rss * 1024,
        }.items():
            self.gauges[name].set(value)
        for shard_id, shard in client.shards.items():
            if math.isfinite(shard.latency):
                self.gauges["gateway.latency"].set(
                    shard.latency, {"shard_id": shard_id}
                )

    def _start_provider_shutdown(self):
        if self.shutdown_thread is not None:
            return
        if self.handler is not None:
            logging.getLogger().removeHandler(self.handler)
            self.handler.close()
        if self.queue_warning_filter is not None:
            logging.getLogger("opentelemetry.sdk._shared_internal").removeFilter(
                self.queue_warning_filter
            )
        self.enabled = False

        def stop():
            # Metrics shut down last so final trace/log processor statistics can
            # be exported. SDK workers and this coordinator are daemon threads.
            for provider in reversed(self.providers):
                try:
                    if provider is getattr(self, "meters", None):
                        provider.shutdown(timeout_millis=2000)
                    else:
                        provider.shutdown()
                except Exception:  # noqa: BLE001 - drain the remaining providers
                    logger.warning("Telemetry provider shutdown failed")

        self.shutdown_thread = threading.Thread(
            target=stop, name="vcroles-telemetry-shutdown", daemon=True
        )
        self.shutdown_thread.start()

    async def close(self):
        if self.shutdown_task is None:
            self.shutdown_task = asyncio.create_task(self._close())
        await asyncio.shield(self.shutdown_task)

    async def _close(self):
        if self.runtime_task is not None:
            self.runtime_task.cancel()
            await asyncio.gather(self.runtime_task, return_exceptions=True)
        self._start_provider_shutdown()
        deadline = time.monotonic() + self.SHUTDOWN_TIMEOUT
        while self.shutdown_thread.is_alive() and time.monotonic() < deadline:
            await asyncio.sleep(0.025)
        if self.shutdown_thread.is_alive():
            logger.warning(
                "Telemetry shutdown budget exhausted; remaining telemetry may be lost"
            )


_active = Telemetry()


def get_telemetry():
    return _active


def trace_context():
    if not _active.enabled:
        return {}
    try:
        from opentelemetry.trace import get_current_span

        context = get_current_span().get_span_context()
        return (
            {
                "trace_id": f"{context.trace_id:032x}",
                "span_id": f"{context.span_id:016x}",
            }
            if context.is_valid
            else {}
        )
    except Exception:  # noqa: BLE001 - trace decoration must not break persisted audit records
        return {}


def start_telemetry():
    global _active
    _active = Telemetry.from_environment()
    return _active


def observed(component):
    """Measure a logical operation without recording its arguments or result."""

    def decorate(function):
        name = _identifier(function.__name__)

        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            with get_telemetry().operation(component, name):
                return await function(*args, **kwargs)

        return wrapper

    return decorate
