# VCRoles OpenTelemetry infrastructure

This is an independent Compose project containing Alloy, Grafana, Loki, Tempo,
Mimir (classic monolithic), and RustFS. It does not load bot code, attach to the
Pelican network, or restart the bot, PostgreSQL, Redis, Wings, or Portainer.
Bot instrumentation is optional and disabled by default; deploying this stack
does not enable telemetry or change the running bot.

## Private access

Grafana binds to loopback by default. To make it accessible through Tailscale,
initialize the deployment with the server's Tailscale IPv4 address as shown
below. Connect through Tailscale and open port `3300` on that address. Login is
required; anonymous access and sign-up are disabled. The username is `admin`.
Retrieve the generated password from the deployment directory in a private
terminal on the server:

```sh
sed -n 's/^GRAFANA_ADMIN_PASSWORD=//p' .env
```

The `.env` file is mode 0600 and is excluded from Git and synchronization.
All S3 users have distinct generated passwords and access only their own bucket.
The S3 console is disabled. Tailscale network policy controls which tailnet users
can reach Grafana. Keep addresses, SSH connection details, credentials, and local
deployment notes outside the repository.

All other published ports bind **127.0.0.1 only**:

| Port | Purpose |
| --- | --- |
| 4317 / 4318 | Alloy OTLP gRPC / HTTP |
| 12345 | Alloy diagnostics and metrics |
| 13100 | Loki diagnostics/query API |
| 13200 | Tempo diagnostics/query API |
| 19009 | Mimir diagnostics/query API |
| 19000 | S3 API for local bootstrap and verification |

Each backend also uses its container hostname on a separate private Docker
bridge. Explicit loopback/Tailscale host bindings restrict external access.
Both OTLP protocols require generated Basic authentication credentials. A
separate internal `vcroles-observability_ingest` network exposes the collector
as `vcroles-collector`, without attaching the backends to that network. Attach
the bot to this network only as part of an approved deployment. No extra host
port needs to be exposed for bot ingestion. Basic authentication supplements
network isolation; it does not provide encryption. Use TLS for any connection
that leaves the local private Docker network or loopback.

## Versions and resources

Every image is pinned by digest in `compose.yaml`: Grafana 13.3.1, Alloy 1.22.0,
Loki 3.7.10, Tempo 3.1.1, Mimir 3.2.5, RustFS 1.0.5, and RustFS CLI 0.1.37.
The CLI is a temporary bootstrap/verification job, not a seventh running service.
Grafana's automatic plugin installation is disabled.

The six services have individual memory/CPU limits totaling 12 GiB RAM and
4.25 logical CPU units. This is a ceiling, not a reservation or sizing forecast.
They run as non-root users with dropped capabilities and no-new-privileges.
Docker stdout logs rotate at 10 MiB with three files per service. RustFS's
native diagnostic files have separate cleanup settings.

All persistent data lives under the deployment's `data/` directory, excluded
from Git and configuration synchronization.
Configuration is mounted read-only. Bind mounts survive container recreation;
ordinary Compose `down` does not delete these data directories.

## Initialize and start a new deployment

On the host, from the directory containing `compose.yaml`:

```sh
python3 scripts/init.py --grafana-bind "$(tailscale ip -4)"
sudo -n sh scripts/up.sh
```

Initialization creates credentials once, sets data directory ownership, and
refuses to overwrite an existing `.env`. It rejects public/all-interface Grafana
bind addresses. Leave the default `127.0.0.1` for a local-only deployment.
The helpers require Docker, Compose, Python 3, and passwordless sudo.

The startup helper checks Compose configuration, starts S3, creates buckets and
scoped users, checks S3 permissions/quota enforcement, starts the remaining
services, and verifies synthetic OTLP data. Rerunning the helper preserves the
generated credentials and data. Configuration changes can recreate only this
project's services; never use it as a way to manage the Pelican bot.

For a deployment initialized before OTLP authentication was added, first run:

```sh
python3 scripts/init.py --upgrade-otlp-auth
sudo -n docker compose up -d --no-deps alloy
```

This adds collector credentials without replacing existing settings. Repeating
the upgrade preserves the generated credentials. Keep `OTLP_PASSWORD` private;
`OTLP_HTPASSWD` supplies Alloy with a hash of the generated random token.

## Pipelines and Grafana

Alloy accepts native OTLP for logs, metrics, and traces. A memory limiter and
bounded sending queues precede export. It also scrapes its own metrics and the
three telemetry backends. No bot log files are scraped.

All application traces are initially retained for measurement. Span metrics and
service graphs are generated on an unsampled branch. Any future trace sampler
must be added only to the Tempo branch, preserving representative metrics.
Do not simultaneously enable duplicate span-metrics generation in Tempo.

Grafana provisions Metrics (`mimir`), Logs (`loki`), and Traces (`tempo`) data
sources, exemplar/trace/log links, service-map configuration, and the
**VCRoles / VCRoles telemetry pipeline** and **VCRoles / VCRoles bot health**
dashboards. Native OTLP metric names in
the pinned Mimir configuration are preserved; for example, the span counter is
`traces_spanmetrics_calls`, not `traces_spanmetrics_calls_total`.

## Retention and storage boundaries

| Backend | Retention | Object quota |
| --- | --- | --- |
| Loki | Seven days, Compactor retention enabled | 12 GiB |
| Tempo | Seven days through the default tenant compaction override | 20 GiB |
| Mimir | Seven days through Compactor retention | 8 GiB |

The bootstrap helper applies these quotas to the object store.
Retention is enforced by the backends; S3 lifecycle expiry is deliberately
absent to avoid deleting index/configuration objects incorrectly. Deletion is
asynchronous and a quota rejects new writes rather than evicting old telemetry.

RustFS initializes a new quota's authoritative usage ledger asynchronously.
The first small write can return `503 SlowDown` until reconciliation completes;
verification retries this transient condition. The actual quota test uses a
disposable 1 MiB bucket, confirms a small round trip, rejects a 2 MiB upload,
and removes the fixture.

Bucket quotas do not bound WALs, caches, Grafana's database, Docker images, or
host logs. They do not impose an overall filesystem quota. Reserve additional
space for working data and compaction; monitor disk use and adjust sampling or
ingestion before quotas fill.

No remote backups or HA are configured. A host/disk failure may lose telemetry.
Alloy's application OTLP queues are bounded in memory and retry downstream
exports for five minutes; restarting Alloy during a downstream outage can lose
queued application data. The Python SDK has separate, shorter export budgets
described below.
Prometheus remote-write uses its own persistent WAL. These limits are intentional
for a disposable telemetry deployment, and do not replace the bot's local
generator audit records.

## Verification and operation

```sh
# Run from the directory containing compose.yaml.
python3 scripts/verify.py
python3 scripts/verify_storage.py
sudo -n docker compose ps
sudo -n docker compose logs --tail 50 alloy
```

`verify.py` sends a unique synthetic trace with a client/server dependency,
a correlated log, a counter, and a histogram with a trace exemplar. It then
queries all three backends, derived span/service-graph metrics, Grafana data
source health, the dashboard, and rejection of anonymous Grafana access.
`verify_storage.py` exercises each S3 user's read/write/delete permissions,
cross-bucket denial, anonymous denial, and actual quota rejection.

`verify_bot.py` exercises the actual Python SDK with synthetic operations, error
classification, runtime metrics, correlated logs, histogram exemplars, and a
redaction sentinel. It uses the separate `vcroles-sdk-validation` service identity
and does not log into Discord or construct database/Redis clients. Run it with
the bot dependencies installed and a local source checkout:

```sh
python3 scripts/verify_bot.py --source-root /path/to/source
```

For an isolated container on the ingestion network, use `--emit-only`,
`--endpoint http://vcroles-collector:4318`, `--collector-env` for a read-only
credentials file, and `--evidence` for a writable result path. Then run
`--existing --evidence /path/to/result` on the host to verify through loopback.

The following explicitly restarts **only the new observability stack** and
briefly stops its three backends. Do not run it during an observability session
where that interruption is unwelcome:

```sh
python3 scripts/verify_recovery.py --allow-service-restarts
```

This verifies uploaded S3 objects, queries the same telemetry after restarting
all six services, and sends fresh OTLP while the three backends are stopped.
After resuming them, it confirms the queued telemetry arrives. It snapshots
unrelated containers' IDs, PIDs, start times, and restart counts and fails if
they change. Local result JSON files contain evidence IDs/outcomes, no secrets.
Short-term recovery tests do not simulate a whole week's age-based deletion.

Fresh telemetry is checked for a metric exemplar that points to its trace.
Mimir retains exemplars in memory/the WAL, rather than long-term S3 blocks;
forced compaction/flush can retire that exemplar history. Recovery checks require
the archived trace, correlated log, and metric data to survive, but do not claim
seven-day exemplar persistence.
[Mimir exemplar storage](https://grafana.com/docs/mimir/latest/manage/use-exemplars/about-exemplars/).

To stop or resume just this project:

```sh
sudo -n docker compose stop
sudo -n docker compose start
```

Keep credentials and data in place. Do not run global Docker prune commands or
delete buckets/WAL directories to make space. When synchronizing configuration,
exclude `.env`, `data/`, and generated validation evidence.

## Bot instrumentation

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

Five Grafana rules cover missing bot telemetry, readiness, database disconnection,
event-loop delay, and SDK drops. They are provisioned **paused**: no notifications
are sent and no contact points or routing policies are created. Configure private
notification routing and review thresholds after production telemetry is enabled,
then change `isPaused` in the provisioning file and reload it. Do not treat the
prepared rules as active monitoring until that rollout is complete.
[Grafana alert provisioning](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/).

Copy the collector's `OTLP_USERNAME` and `OTLP_PASSWORD` into the bot's private
environment as `VCROLES_OTEL_USERNAME` and `VCROLES_OTEL_PASSWORD`. Set
`OTEL_EXPORTER_OTLP_ENDPOINT=http://vcroles-collector:4318` and
`VCROLES_OTEL_ENABLED=1`. The bot loads its local `.env` without overriding
process environment variables. `VCROLES_OTEL_ENVIRONMENT` defaults to
`development`; `OTEL_SERVICE_NAME` defaults to `vcroles`. Neither endpoint nor
credentials are written into the public configuration.

During deployment, with `BOT_CONTAINER` set privately to the intended container:

```sh
sudo -n docker network connect vcroles-observability_ingest "$BOT_CONTAINER"
```

Make the network attachment persistent in the container-management workflow;
manual Docker attachment does not survive replacement of a Pelican container.
Enabling the SDK requires an approved bot rollout/restart. The stack helpers
never perform that step. Set `VCROLES_OTEL_ENABLED=0` to disable it on a future
restart; telemetry configuration errors also leave application work running and
produce a local warning without including credentials.

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

Only structured event names, allowlisted numeric/boolean context fields, and
validated generated operation UUIDs are exported as logs. Raw log messages,
SQL/arguments/results, exception messages and
tracebacks, tokens, user content, Discord IDs, host names, and command lines are
excluded. Existing
detailed local logs and generator audit persistence remain
independent; local JSON records gain trace/span IDs when a span is active.
Direct Redis/HTTP attempt instrumentation and server-side database metrics can
be added without automatically exporting request payloads or SQL text.
