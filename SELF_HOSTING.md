# Self Hosting

This is a simple guide to help you set up the bot on your own server. It is not intended to be comprehensive, but it should provide enough information to get you started.

I will not provide any additional support for self-hosting other than what is documented here.

## Requirements

-   A PostgreSQL database
-   A Redis instance
-   Python 3.11 or higher (might work with versions below, but not tested)

You will need to work out how to set up a basic PostgreSQL database and a Redis instance on your own. There are many resources available online for this, and it is beyond the scope of this guide to cover them in detail.

## Configuration

To configure the bot, you will need to create a `.env` file as well as a `config.py` file. You can copy the provided `config.example.py` to `config.py` and fill in the required values, as well as copy the `.env.example` to `.env` and fill in the required values.

### Key Configuration Items

**Discord Bot Token**: You'll need to create a Discord application and bot at https://discord.com/developers/applications and copy the bot token to the `BOT_TOKEN` field in `config.py`.

**Database**: The `.env` file stores the PostgreSQL database connection string. Update the `DATABASE_URL` with your database credentials.

**Redis**: Configure your Redis connection details in the `REDIS` class in `config.py`.

**Environment**: Keep `ENVIRONMENT` set to `"DEV"` for self-hosting. The `"PROD"` setting enables Top.gg integration which is not needed for personal use.

**Webserver**: The bot runs a status endpoint on `WEBSERVER_PORT` (default 5000) for health checking.

## Requirements Installation

All requirements are specified in the `requirements.txt` file. The recommended way to install them is via `uv`:

```bash
uv venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

## Database Setup

For interacting with the PostgreSQL database, we use the Prisma library. To ensure the database has the correct schema, follow these steps:

1. Create a PostgreSQL database for the bot.
2. Update the `DATABASE_URL` in the `.env` file with the connection string for your database.
3. Run the following command to create the necessary tables:

```bash
prisma db push
```

Alternatively, you may need to use the following command if prisma is not found:

```bash
python -m prisma db push
```

This will push the schema defined in `prisma/schema.prisma` to your PostgreSQL database, as well as generating the Python client for Prisma.

If the generation fails for whatever reason, you can manually run the following command to generate the Prisma client:

```bash
prisma generate
# OR
python -m prisma generate
```

## Running the Bot

Running the bot is straightforward. You simply run the `bot.py` file:

```bash
python bot.py
```

## Persistent logs

Logs are appended immediately to `logs/vcroles.jsonl`. Generator creation and
cleanup operations also write to `logs/generator-audit.jsonl`. These files contain
one JSON record per line, with UTC timestamps, a process run ID, the Git revision,
operation context, and exception tracebacks. TTS message text and nickname values
are not added to the new diagnostic events.

The console uses coloured levels, logger names, and tracebacks when attached to
a terminal. Set `FORCE_COLOR=1` to enable colours in a panel that does not expose
a TTY. Set `NO_COLOR` or `FORCE_COLOR=0` to disable them. Persisted JSON logs stay
plain, regardless of the console setting.

Diagnostics include shard ready/disconnect/resume events, readiness changes
observed by `/status` polls, shutdown requests and cleanup, member-edit and
database failures, and TTS lifecycle/FFmpeg failures. Generator audit events
include operation IDs, channel IDs, cleanup reasons, and deletion outcomes.
Revisions include `+dirty` when tracked local changes are present at startup.

The main log rotates at 20 MiB and the audit log at 5 MiB; each retains ten
backups (`.1` through `.10`). Restarts append to the current files instead of
truncating them. Old `bot.log` and `discord.log` files are left untouched, but are
no longer written. The owner-only logs command uses the new main log.

Every record is flushed before the logging call returns. Error records and all
audit records additionally use `fsync`. A generator delete intent must be
successfully persisted before a delete request is sent to Discord. The outcome
is recorded separately; an intent without an outcome means the result needs
investigation. Creation operation IDs are also included in Discord's audit-log
reason, allowing correlation if a creation response is lost.

Set `VCROLES_LOG_DIR` to choose another directory. Keep that directory on the
container's persistent volume if containers may be replaced. Logging setup fails
if the files cannot be opened. Later main-log write failures are reported to
stderr; audit write failures stop the affected generator operation. Rotation
bounds storage use, so copy files elsewhere if longer retention is needed.

These are local file guarantees: they do not provide remote backups or make a
Discord API request and a local audit record a single transaction. A hard kill
can leave a partial final record; the next startup separates it from subsequent
records without discarding the existing history.
Host-triggered restarts, out-of-memory kills, and `SIGKILL` still require the
hosting panel's exit code and restart metadata; the process cannot log after it
has been killed.

## Optional OpenTelemetry

The bot supports optional traces, metrics, and structured event export over
authenticated OTLP/HTTP. It is disabled by default. See
[the observability guide](observability/README.md#bot-instrumentation) for the
private collector connection, environment variables, exported fields, resource
limits, and shutdown behavior. Detailed local logs and generator audit records
continue to work without a collector.
