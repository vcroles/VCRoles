from __future__ import annotations

import datetime
from typing import Any, Optional

import discord
import redis.asyncio as aioredis
from discord.ext import commands

import config
from utils.database import DatabaseUtils
from utils.types import LogLevel, using_topgg
from views.interface import Interface


class VCRolesClient(commands.AutoShardedBot):
    def __init__(
        self,
        ar: aioredis.Redis[Any],
        db: DatabaseUtils,
        intents: discord.Intents,
        console_log_level: LogLevel,
    ):
        self.ar = ar
        self.db = db
        self.log_queue: list[str] = []
        self.console_log_level = console_log_level
        super().__init__(
            intents=intents,
            command_prefix=commands.when_mentioned,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Voice Channels",
            ),
            status=discord.Status.online,
        )
        self.persistent_views_added = False
        if using_topgg:
            import topgg

            self.topgg_webhook: Optional[topgg.WebhookManager]

    def incr_counter(self, cmd_name: str):
        """Increments the counter for a command"""
        self.loop.create_task(self.ar.hincrby("counters", cmd_name, 1))

    def incr_role_counter(self, action: str, count: int = 1):
        """
        action: `add` or `remove`.
        Increments the counter for roles added or removed
        """
        self.loop.create_task(self.ar.hincrby("counters", f"roles_{action}", count))

    async def on_ready(self):
        """
        Called when the bot is ready.
        """
        if not self.persistent_views_added:
            self.add_view(Interface(self.db))
            self.persistent_views_added = True

        if hasattr(self, "topgg_webhook") and self.topgg_webhook and using_topgg:
            if self.topgg_webhook.is_running:
                print("TopGG webhook is running")
            else:
                await self.topgg_webhook.start(config.DBL.WEBHOOK_PORT)

        print(f"Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds.")

        mapping: dict[int, int] = {}
        for guild in self.guilds:
            mapping[guild.shard_id] = mapping.get(guild.shard_id, 0) + 1
        for shard_id, count in mapping.items():
            print(f"Shard {shard_id}: {count}")

        print("------")

    async def on_guild_join(self, guild: discord.Guild):
        self.incr_counter("guilds_join")

        await self.db.guild_add(guild.id)

    async def on_guild_remove(self, guild: discord.Guild):
        self.incr_counter("guilds_leave")

        await self.db.guild_remove(guild.id)

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """
        When a channel is deleted, remove it from the database.
        """
        await self.db.db.link.delete_many(
            where={"id": str(channel.id), "guildId": str(channel.guild.id)}
        )
        await self.db.db.voicegenerator.delete_many(
            where={"generatorId": str(channel.id), "guildId": str(channel.guild.id)}
        )

    async def close(self) -> None:
        await self.db.disconnect()

        return await super().close()

    async def setup_hook(self) -> None:
        await self.db.connect()

        return await super().setup_hook()

    def log(self, level: LogLevel, message: str) -> None:
        """Logs a message to the console"""
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        if level <= self.console_log_level:
            print(
                f"\x1b[30;1m{timestamp}\x1b[0m {level}{(8-len(level.name))*' '} \x1b[35minternal.bot\x1b[0m {message}"
            )

        self.log_queue.append(
            timestamp
            + " "
            + level.name
            + (8 - len(level.name)) * " "
            + " internal.bot "
            + message
        )
