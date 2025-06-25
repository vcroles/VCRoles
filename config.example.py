from typing import Literal

# The bot token is used to authenticate the bot with Discord.
BOT_TOKEN = "your-bot-token-here"


# Configuration for the Redis connection
class REDIS:
    HOST = "localhost"
    PORT = 6379
    DB = 0
    PASSWORD = "your-redis-password-here"


# Environment can either be "DEV" or "PROD".
# If you set it to "PROD", the bot will try and connect to Top.gg
# Other than this, there are no differences in functionality.
# I'd recommend keeping it set as "DEV" while self-hosting.
ENVIRONMENT: Literal["DEV", "PROD"] = "DEV"

# The webserver port is used to host a status endpoint for the bot.
WEBSERVER_PORT = 5000


class DBL:
    """
    Configuration for the DBL (Top.gg) integration.
    Leave values as-is if you don't want to use Top.gg integration.
    """

    TOKEN = ""
    WEBHOOK_PASSWORD = ""
    WEBHOOK_PORT = 5021
