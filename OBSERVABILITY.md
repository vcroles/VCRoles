# Optional OpenTelemetry

The bot can export traces, metrics and structured events over authenticated
OTLP/HTTP to any OpenTelemetry collector. It is disabled by default, and the bot
runs normally without a collector. Detailed local logs and generator audit
records are independent of it.

The maintainers' collector, dashboards and alert rules live in a separate
private repository; this document covers only the bot's side.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `VCROLES_OTEL_ENABLED` | off | Set to `1` to enable export. `0` disables it on the next restart. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | The collector's OTLP/HTTP base URL. Keep it private (loopback, a private network or a VPN); Basic auth is not encryption. |
| `VCROLES_OTEL_USERNAME`, `VCROLES_OTEL_PASSWORD` | — | The collector's Basic auth credentials. |
| `VCROLES_OTEL_ENVIRONMENT` | `development` | `deployment.environment` resource attribute. |
| `OTEL_SERVICE_NAME` | `vcroles` | Service name. |
| `OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED` | on | Set to `false` to disable the SDK's own queue and drop metrics. |

The bot loads its local `.env` without overriding process environment
variables. The endpoint and credentials are never written into the public
configuration. Telemetry configuration errors leave the bot running and produce
a local warning that doesn't include credentials.

## What is instrumented

Instrumentation covers shard ready/disconnect/resume traces and
counters, readiness and health-request outcomes, per-shard gateway latency,
event-loop lag, task/guild counts, peak process RSS, database connection state,
and logical `DatabaseUtils` operation durations/outcomes. Database timing
includes cache hits; it is not SQL execution timing and does not cover direct
Prisma calls outside that utility. Span names and metric dimensions are static
operation names, outcomes, and bounded shard/status values.

Command callback traces use static cog/method names and preserve command schemas.
They measure callback execution, excluding permission checks before invocation;
they do not measure the exact acknowledgement time. Member-edit batches have
independent root traces with up to eight links to the originating voice events,
plus queue-wait, lock-wait, completion, and backlog measurements. Additional
source links are counted and omitted. Update counts include every coalesced
queue entry, while batch spans represent one dispatched edit.

Generator operations have nested lifecycle spans and audit-event counters. TTS
separates synthesis, voice connection, playback, and cleanup, including a link
from audio-thread cleanup to its source context. Caught, logged failures mark
active operations as containing an error; cancellation is recorded separately.
Generator operation UUIDs are allowed in exported log metadata, never metric
labels. No user-supplied command arguments, nicknames, or TTS text are exported.

## Limits and shutdown

The SDK exports at most 1 MiB per request with a two-second export budget,
queues up to 1,024 spans and 512 logs, and exports metrics every 15 seconds.
Metrics have an attribute allowlist and a 2,048-series limit per instrument.
Telemetry is exported by SDK background threads. Shutdown waits at most five
seconds for export cleanup, then permits process exit with potential telemetry
loss. Queue saturation drops telemetry; SDK queue/drop metrics expose that loss,
and repeated queue-full warnings are limited to one per signal per 30 seconds.
SDK internal metrics can be disabled with
`OTEL_PYTHON_SDK_INTERNAL_METRICS_ENABLED=false`.
Collector requests use dedicated sessions that ignore environment proxies and
`.netrc`, keeping private credentials on the configured direct connection.
The SDK permits configurable HTTPS destinations; keeping ingestion private is
also a deployment requirement, not an outbound firewall enforced by the SDK.

## Exported fields

Only structured event names, allowlisted numeric/boolean context fields, and
validated generated operation UUIDs are exported as logs. Raw log messages,
SQL/arguments/results, exception messages and
tracebacks, tokens, user content, Discord IDs, host names, and command lines are
excluded. Existing
detailed local logs and generator audit persistence remain
independent; local JSON records gain trace/span IDs when a span is active.
Direct Redis/HTTP attempt instrumentation and server-side database metrics can
be added without automatically exporting request payloads or SQL text.

