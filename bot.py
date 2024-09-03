from __future__ import annotations

import asyncio
import os
from typing import Any

import discord
import redis.asyncio as aioredis
from discord import app_commands

import config
from utils.client import VCRolesClient
from utils.database import DatabaseUtils
from utils.logging import setup_logging
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
        return await interaction.response.send_message(
            "You do not have the required permissions to use this command.",
            ephemeral=True,
        )
    if isinstance(error, app_commands.BotMissingPermissions):
        return await interaction.response.send_message(
            error,
            ephemeral=True,
        )
    else:
        client.log(
            LogLevel.ERROR,
            f"Command Error: g/{interaction.guild_id} {error}",
        )


async def main():
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

    with open("bot.log", "w") as f:
        f.write("")

    async with client:
        # Adding Extensions

        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded extension: {filename[:-3]}")

        await client.load_extension("jishaku")

        await client.start(config.BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
