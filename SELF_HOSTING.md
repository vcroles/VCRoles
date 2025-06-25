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
