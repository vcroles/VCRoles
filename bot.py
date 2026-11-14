from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

import discord
import redis.asyncio as aioredis
from discord import app_commands
from dotenv import load_dotenv

import config
from utils.client import VCRolesClient
from utils.database import DatabaseUtils
from utils.logging import setup_logging
from utils.telemetry import start_telemetry
from utils.types import LogLevel

setup_logging()

intents = discord.Intents(guilds=True, voice_states=True, dm_messages=True)

ar: aioredis.Redis[Any] = aioredis.Redis(
    host=config.REDIS.HOST,
    password=config.REDIS.PASSWORD,
    port=config.REDIS.PORT,
    db=config.REDIS.DB,
    decode_responses=True,
)
db_utils = DatabaseUtils()

client = VCRolesClient(
    ar, intents=intents, db=db_utils, console_log_level=LogLevel.ERROR
)
client.remove_command("help")


@client.tree.error
async def on_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "You do not have the required permissions to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
        message = str(error)
    else:
        client.log(
            LogLevel.ERROR,
            "Application command failed",
            error=getattr(error, "original", error),
            event="command_failed",
            guild_id=interaction.guild_id,
            member_id=interaction.user.id,
            channel_id=interaction.channel_id,
            interaction_id=interaction.id,
            command=getattr(interaction.command, "qualified_name", None),
        )
        message = "Something went wrong while running this command. Please try again."

    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException as response_error:
        client.log(
            LogLevel.ERROR,
            "Could not send command error",
            error=response_error,
            event="command_error_response_failed",
            interaction_id=interaction.id,
            guild_id=interaction.guild_id,
        )


async def run_bot():
    logging.getLogger(__name__).info(
        "Starting bot process pid=%s, Python=%s, discord.py=%s",
        os.getpid(),
        sys.version.split()[0],
        discord.__version__,
    )
    # Removing TTS Files

    for filename in os.listdir("tts"):
        if filename.endswith(".mp3"):
            os.remove(f"tts/{filename}")

    # Setting up guild count file

    try:
        with open("guilds.csv", "r") as f:
            f.read()
    except FileNotFoundError:
        with open("guilds.csv", "w") as f:
            f.write("datetime,guilds,shards\n")

    async with client:
        # Adding Extensions

        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded extension: {filename[:-3]}")

        await client.load_extension("jishaku")

        try:
            await client.start(config.BOT_TOKEN)
        except asyncio.CancelledError:
            logging.getLogger(__name__).warning("Bot main task was cancelled")
            raise
        except Exception:
            logging.getLogger(__name__).exception("Bot stopped with an unhandled error")
            raise
        else:
            logging.getLogger(__name__).warning("Discord client.start() returned")


async def main():
    load_dotenv()
    telemetry = start_telemetry()
    try:
        await run_bot()
    finally:
        await telemetry.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot process interrupted")
    except Exception:
        logging.getLogger(__name__).exception(
            "Bot process failed during startup, operation, or cleanup",
            extra={"event": "process_failed"},
        )
        raise
    finally:
        logging.shutdown()
