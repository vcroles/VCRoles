"""Exercise the bot SDK with synthetic operations, without logging into Discord.

Emission needs the bot's Python dependencies/source. --existing only needs the
standard library and queries the stack through loopback. No real database or
Redis client is constructed, and no production container is used.
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import sys
import time
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

from verify import ROOT, eventually, request

SERVICE = "vcroles-sdk-validation"
PRIVATE_SENTINEL = "sdk-test-secret-and-user-content-must-not-be-exported"


async def emit(args):
    sys.path.insert(0, str(args.source_root))
    from utils.telemetry import start_telemetry

    config = dict(
        line.split("=", 1)
        for line in args.collector_env.read_text().splitlines()
        if line and not line.startswith("#")
    )
    os.environ.update(
        {
            "VCROLES_OTEL_ENABLED": "1",
            "OTEL_SERVICE_NAME": SERVICE,
            "OTEL_EXPORTER_OTLP_ENDPOINT": args.endpoint,
            "VCROLES_OTEL_USERNAME": config.get(
                "OTLP_USERNAME", config.get("VCROLES_OTEL_USERNAME", "")
            ),
            "VCROLES_OTEL_PASSWORD": config.get(
                "OTLP_PASSWORD", config.get("VCROLES_OTEL_PASSWORD", "")
            ),
            "VCROLES_OTEL_ENVIRONMENT": "validation",
        }
    )
    telemetry = start_telemetry()
    if not telemetry.enabled:
        raise RuntimeError("SDK initialization failed")
    started = time.time_ns()
    try:
        with telemetry.operation("validation", "sdk_probe"):
            from opentelemetry.trace import get_current_span

            trace = f"{get_current_span().get_span_context().trace_id:032x}"
            with telemetry.operation("database", "sdk_validation"):
                await asyncio.sleep(0.01)
            try:
                with telemetry.operation("database", "sdk_validation_error"):
                    raise ValueError(PRIVATE_SENTINEL)
            except ValueError:
                logging.getLogger("internal.bot").exception(
                    PRIVATE_SENTINEL,
                    extra={
                        "event": "sdk_validation",
                        "context": {"status": 503, "sql": PRIVATE_SENTINEL},
                    },
                )
            from utils.logging import audit_event

            audit_event(
                "generator_validation",
                error=ValueError(PRIVATE_SENTINEL),
                operation_id="a" * 32,
            )
            telemetry.gateway("ready", 0)
            telemetry.health(200)
            telemetry._sample_runtime(
                SimpleNamespace(
                    is_ready=lambda: True,
                    db=SimpleNamespace(db=SimpleNamespace(is_connected=lambda: True)),
                    guilds=[],
                    shards={},
                ),
                0.01,
            )
            source = telemetry.capture_context()
        with telemetry.operation("member_edit", "sdk_batch", links=[source], root=True):
            batch_trace = f"{get_current_span().get_span_context().trace_id:032x}"
            times = [time.monotonic() - 1, time.monotonic() - 0.5]
            telemetry.queue_started(times)
            await asyncio.sleep(0.01)
            telemetry.queue_finished(times, "success")
    finally:
        await telemetry.close()
    if telemetry.shutdown_thread.is_alive():
        raise RuntimeError("SDK validation did not shut down within its budget")
    return {
        "trace_id": trace,
        "batch_trace_id": batch_trace,
        "instance": telemetry.resource.attributes["service.instance.id"],
        "emitted_at_ns": started,
    }


def verify(evidence):
    trace = evidence["trace_id"]
    data = eventually(
        "bot SDK trace", lambda: request(f"http://127.0.0.1:13200/api/traces/{trace}")
    )
    if PRIVATE_SENTINEL in json.dumps(data):
        raise RuntimeError("Private exception text leaked into SDK trace")
    batch = eventually(
        "bot SDK detached batch trace",
        lambda: request(
            f"http://127.0.0.1:13200/api/traces/{evidence['batch_trace_id']}"
        ),
    )
    encoded = base64.b64encode(bytes.fromhex(trace)).decode()
    if trace not in json.dumps(batch) and encoded not in json.dumps(batch):
        raise RuntimeError("Batch trace is missing its source link")
    query = urllib.parse.urlencode(
        {
            "query": f'{{service_name="{SERVICE}"}} |= "sdk_validation"',
            "start": str(evidence["emitted_at_ns"] - 1_000_000_000),
            "end": str(evidence["emitted_at_ns"] + 60_000_000_000),
        }
    )
    logs = eventually(
        "bot SDK correlated log",
        lambda: request(f"http://127.0.0.1:13100/loki/api/v1/query_range?{query}")[
            "data"
        ]["result"],
    )
    if trace not in json.dumps(logs) or PRIVATE_SENTINEL in json.dumps(logs):
        raise RuntimeError("SDK log correlation/redaction check failed")
    identity = f'job="{SERVICE}",instance="{evidence["instance"]}"'
    for name, labels in (
        (
            "vcroles_operations",
            'component="database",operation="sdk_validation",outcome="success"',
        ),
        (
            "vcroles_operations",
            'component="database",operation="sdk_validation_error",outcome="error"',
        ),
        (
            "vcroles_operation_duration_bucket",
            'component="database",operation="sdk_validation"',
        ),
        ("vcroles_bot_ready", ""),
        ("vcroles_gateway_events", 'event="ready",shard_id="0"'),
        ("otel_sdk_processor_span_processed", ""),
        ("vcroles_member_edit_queue_events", 'outcome="success"'),
        ("vcroles_member_edit_queue_wait_bucket", ""),
        ("vcroles_member_edit_queue_completion_bucket", 'outcome="success"'),
        ("vcroles_generator_events", 'event="generator_validation"'),
        ("vcroles_process_rss", ""),
        ("vcroles_process_cpu_time", ""),
        ("vcroles_process_threads", ""),
        ("vcroles_process_open_fds", ""),
    ):
        expression = f"{name}{{{identity}{',' + labels if labels else ''}}}"
        query = urllib.parse.urlencode(
            {"query": expression, "time": evidence["emitted_at_ns"] / 1e9 + 60}
        )
        eventually(
            f"bot SDK metric {expression}",
            lambda query=query: request(
                f"http://127.0.0.1:19009/prometheus/api/v1/query?{query}"
            )["data"]["result"],
        )
    query = urllib.parse.urlencode(
        {
            "query": f"vcroles_operation_duration_bucket{{{identity}}}",
            "start": evidence["emitted_at_ns"] / 1e9 - 1,
            "end": evidence["emitted_at_ns"] / 1e9 + 60,
        }
    )
    eventually(
        "bot SDK histogram exemplar",
        lambda: (
            trace
            in json.dumps(
                request(
                    f"http://127.0.0.1:19009/prometheus/api/v1/query_exemplars?{query}"
                )["data"]
            )
        ),
    )
    print(
        "PASS actual bot SDK export, trace/log correlation, metrics, and redaction",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emit-only", action="store_true")
    parser.add_argument("--existing", action="store_true")
    parser.add_argument("--source-root", type=Path, default=ROOT.parent)
    parser.add_argument("--collector-env", type=Path, default=ROOT / ".env")
    parser.add_argument("--endpoint", default="http://127.0.0.1:4318")
    parser.add_argument(
        "--evidence", type=Path, default=ROOT / "bot-validation-results.json"
    )
    args = parser.parse_args()
    if args.existing:
        evidence = json.loads(args.evidence.read_text())
    else:
        evidence = asyncio.run(emit(args))
        args.evidence.write_text(json.dumps(evidence, indent=2) + "\n")
    if not args.emit_only:
        verify(evidence)


if __name__ == "__main__":
    main()
