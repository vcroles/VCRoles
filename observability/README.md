# VCRoles OpenTelemetry infrastructure

This is an independent Compose project containing Alloy, Grafana, Loki, Tempo,
Mimir (classic monolithic), and RustFS. It does not load bot code, attach to the
Pelican network, or restart the bot, PostgreSQL, Redis, Wings, or Portainer.
The bot is not instrumented or connected to this collector yet.

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
The collector has no application authentication and accepts local traffic only.
Before connecting the bot, choose and validate its restricted network path and
authentication separately.

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
**VCRoles / VCRoles telemetry pipeline** dashboard. Native OTLP metric names in
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
Application OTLP queues are bounded in memory and retry for five minutes;
restarting Alloy during a downstream outage can lose queued application data.
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
