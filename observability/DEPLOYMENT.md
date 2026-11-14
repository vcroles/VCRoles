# Bot rollout

The infrastructure can run and collect external metrics before the bot is
updated. Pushing code, changing the production bot environment and restarting
the bot are separate rollout actions; the preparation tools do not perform them.

## Durable private connection

For a Pelican-managed bot, `compose.bot-network.yaml` publishes authenticated
OTLP/HTTP on the same Tailscale IPv4 address configured for Grafana. The bot's
existing application bridge can reach this host address. This avoids manually
attaching each replacement bot container to the collector's Docker network.
Only port `4318` is added, bound to that private address; the storage metrics
listener is not published. Keep the Tailscale address and collector credentials
in the private deployment `.env`.

```sh
python3 scripts/prepare_bot_environment.py
```

This requires a Tailscale Grafana binding and creates `.bot-telemetry.env` with
mode `0600`, without printing its contents or changing the production bot.
Existing proposals are preserved unless `--replace` is specified. The proposal
enables SDK export, selects the production environment, and includes the private
endpoint and generated credentials. Do not commit this file or paste it into a
public issue.

For the full deployment, set the following in the observability stack's private
`.env` so future Compose operations preserve all selected overlays:

```text
COMPOSE_FILE=compose.yaml:compose.monitoring.yaml:compose.bot-network.yaml
```

Then apply the collector change, leaving the bot running:

```sh
sudo -n docker compose config --quiet
sudo -n docker compose up -d --no-deps alloy
```

Use `--force-recreate` when applying changes to an individually bind-mounted
collector configuration file. Including all selected files matters: explicitly
using a partial `-f` list can remove the additional listener. Docker retains the
listener through ordinary collector restarts. It requires Tailscale's address
to be available on the host.

The existing internal `vcroles-collector` alias remains an alternative for bots
whose container-management workflow already persists the ingestion-network
attachment. Use one endpoint consistently. Internal Docker traffic stays on the
host; connections arriving through Tailscale use its encrypted transport. Basic
authentication is required on the application receiver in either case.

## Approved production rollout

After reviewing and approving the code and deployment:

1. Publish and merge the reviewed branch through the normal repository workflow.
2. Keep a private backup of the current application environment outside the
   checkout. Merge the prepared telemetry variables into the bot's existing
   environment, preserving its database and other settings.
3. Restart the bot through its normal hosting workflow so it pulls the approved
   code and installs the pinned dependencies.
4. Confirm readiness, shard health, fresh `vcroles` telemetry and correlations.
   Compare CPU, RSS, event-loop delay, exporter drops and ingestion growth with
   the external container/database measurements.
5. Review alert thresholds and configure private notification routing before
   unpausing alerts. The provisioned rules start paused and send no messages.

No bot network attachment is needed with the Tailscale listener, including after
container replacement. A failed collector export does not block bot operations.
To disable SDK export, set `VCROLES_OTEL_ENABLED=0` and use an approved restart;
local logs and generator audits remain available. Keep the previous approved
code revision available for a code rollback if application behavior regresses.
