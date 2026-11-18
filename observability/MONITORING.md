# Host, container, and database monitoring

The optional `compose.monitoring.yaml` adds a metrics-only Alloy agent. It embeds
node_exporter, cAdvisor, postgres_exporter, and redis_exporter and writes to the
existing Mimir instance. Collection does not require changes to the running bot.
The bot SDK separately provides its Python process CPU time, current RSS/VMS,
threads, and open file descriptors once the SDK is enabled.

Grafana provisions three additional dashboards:

- **VCRoles host and runtime**: host CPU, memory, disk, load and selected container
  CPU, memory, disk I/O and network traffic, plus optional Python process metrics.
- **VCRoles application databases**: PostgreSQL availability, connections, database
  sizes, transactions, buffer hits, locks, deadlocks and temporary storage;
  Redis availability, memory, clients, commands, cache hits, evictions and traffic.
- **VCRoles observability backends**: Loki, Tempo and Mimir process/ingestion state,
  RustFS capacity, usage, quotas and request latency, and Grafana SQLite pools.

Container CPU includes all processes, including Prisma and FFmpeg. A value of
100% means one logical CPU core; host CPU utilization is normalized across cores.
Python process metrics exclude subprocesses. Disk I/O counters reflect physical
I/O charged to the container, rather than every application read or write.

The memory comparison panel places Python RSS, container RSS and container working
set together. These overlap and use different accounting; they are not additive,
and their difference is not an exact measurement of Prisma or another child.

Latency panels distinguish HTTP requests from Tempo's internal scheduler long
polls. Backend HTTP percentiles exclude gRPC, scrape and readiness traffic and
have a companion request-volume panel. RustFS uses mean request latency because
its native histogram's first nonzero bucket spans 0–5 seconds; that histogram
cannot resolve a useful p95 for normal requests. Histogram percentiles are
estimates, especially for sparse command/TTS observations; the bot dashboard
includes counts over the same rate window.

Redis and PostgreSQL hit ratios have gaps when their denominator is zero.
An idle window is not a 0% hit rate. Redis read rates and command breakdowns
separate keyspace lookups from analytics increments and exporter traffic.

The telemetry pipeline shows exports, failures, receiver outcomes and queue
utilization for each configured signal. A missing exporter error counter becomes
zero only while its sent counter is present and Alloy is being scraped
successfully. SDK error counters similarly use the corresponding queue gauge as
their presence check. Missing telemetry remains a gap. The service graph is
explicitly labelled as synthetic validation traffic; production dependency edges
require additional client/server instrumentation.

The member-edit queue and active-batch panels remain instantaneous five-second
samples. Because dispatch also runs every five seconds, timing drift can produce
a slow sawtooth or periodic worker spikes. These panels do not measure interval
peaks; use queue-wait/completion histograms and means to assess processing delay.

Object-store quota utilization is a combined total, not proof that every bucket
has headroom. The net-growth panel scales a six-hour usage trend to bytes/day;
retention and compaction can make it negative. It is not an ingestion measure or
a guarantee about future storage use.

## Bot process freshness and permission retries

The bot health dashboard includes a **Process instance** selector. All retains
the selected service's process history across restarts. Health gauges select
the newest process at each evaluation time and require both readiness telemetry
and their own samples to be less than 60 seconds old. Readiness can be zero and
still be fresh. Old process values therefore stop appearing as current health
when the replacement starts reporting, rather than lingering through Mimir's
default five-minute lookback. Missing telemetry remains a gap or unknown value.

The same freshness handling applies to Python runtime gauges. Counter rates,
observation windows and percentiles retain selected process history; earlier
work should still contribute to the period being queried. The telemetry-age
panels deliberately show aging readiness samples until query lookback expires.
Their age measures export freshness, not an independent HTTP availability check
or proof that the asynchronous runtime sampler is progressing.

The bot dashboard's **Permission backoff** section shows cooldown scheduling,
suppressed checks, clearances/rechecks, deferred queued entries, and scheduling
reasons. A log panel exposes retry decisions and their correlated traces.
Schedules include cached permission checks and do not imply an HTTP error;
suppressed checks are not unique users or precise counts of avoided requests.
There is no active-resource gauge, and event series that have never occurred
can be absent. See [permission retry behavior](../PERMISSION_RETRIES.md).

These dashboard JSON files are provisioned from a directory mount. Updating
them requires no bot or backend restart; Grafana reloads the files. Alert pause
states and notification routing are managed separately.

## Private configuration

Create `monitoring-targets.json` locally on the deployment host with mode `0600`.
It must contain string fields `postgres_dsn`, `redis_addr`, `redis_password`,
`bot_container`, `postgres_container`, and `redis_container`. Keep actual addresses,
container identities and credentials outside Git. Use a PostgreSQL monitoring
login with `pg_monitor`, connection access, read-only session defaults, a short
statement timeout and a small connection limit. Do not use the application
database owner's credentials for this exporter.

The Redis collector uses the supplied private authentication. Its enabled
collection reads server statistics; key scans, key-value export, client lists,
and CONFIG collection are disabled. Using an existing Redis password does not
make that credential read-only. A dedicated ACL account can be used where its
permissions and persistence are managed by the database operator.

From the observability deployment directory:

```sh
chmod 600 monitoring-targets.json
python3 scripts/configure_monitoring.py
sudo -n docker compose -f compose.yaml -f compose.monitoring.yaml up -d --no-deps metrics-agent
python3 scripts/verify_monitoring.py
```

The configuration helper creates `.metrics.env` atomically with mode `0600` and
prepares the persistent WAL directory. It does not create database roles, modify
Redis, or restart production services. Replacing existing settings requires
`--replace`. The overlay requires Compose supporting raw `env_file` values
(2.30 or later), so passwords containing dollar signs and quotes remain literal.

The metrics agent runs as root with the host PID/network namespaces and read-only
host mounts. It drops all Linux capabilities and does not use privileged mode.
Its Docker socket access is nevertheless root-equivalent: a read-only socket
mount does not restrict Docker API methods. Keep this trusted agent separate
from the application OTLP receiver. Its HTTP diagnostics bind only to loopback
on port `12346`; no new public metrics endpoint is created.

Container identities and images are removed before ingestion; selected services
are mapped to fixed role labels. Host and database target instance labels are
normalized. A 30-second scrape interval and a one-hour remote-write WAL bound
the collector's retry storage. Its configured ceiling is 768 MiB RAM and
0.75 logical CPU units; tune from observed workload and query cost.

## Storage and Grafana telemetry

RustFS pushes native OTLP metrics to the collector's telemetry-network-only
`storage-collector` listener. It is not published on the host or bound to the bot
ingestion interface. Storage logs and traces are not exported through this path.
An aggregation processor retains only bounded operation/stage/status dimensions,
combining object paths and bucket dimensions before Mimir ingestion. Bucket usage
and quota panels therefore show combined totals. This reduces cardinality and
keeps object keys out of metric labels.
[RustFS observability](https://docs.rustfs.com/en/operations/observability).

Grafana's native metrics include its SQLite connection-pool state. No extra
SQLite exporter, database-file mount, or database credential is needed. The
existing private scrape also covers Loki, Tempo and Mimir's native Go/process
and backend metrics. These complement their container resource measurements.

Host/database alert rules are provisioned paused, alongside the bot rules.
Review thresholds and notification routing before enabling them. Missing SDK
panels before a bot rollout are expected; the external container/database
panels can already report the running services.

When applying collector file changes after synchronization, recreate the
collectors explicitly. Individual bind-mounted files may still refer to an old
inode after an atomic file replacement:

```sh
sudo -n docker compose -f compose.yaml -f compose.monitoring.yaml up -d --force-recreate --no-deps alloy metrics-agent
```

This restarts only the observability collectors. Avoid doing it during a
downstream outage if losing in-memory OTLP queues would be unwelcome. The
metrics agent's WAL survives recreation. Include both Compose files whenever
managing this optional agent; never use `--remove-orphans` to manage the bot.
