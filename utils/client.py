from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

import aiohttp
import discord
import redis.asyncio as aioredis
from cachetools import TTLCache
from discord.ext import commands

from utils.database import DatabaseUtils
from utils.gateway import configure_gateway_compression
from utils.telemetry import get_telemetry, observed
from utils.types import LogLevel
from views.interface import Interface

logger = logging.getLogger(__name__)


class VCRolesClient(commands.AutoShardedBot):
    entitlements_cache: TTLCache[Any, Any] = TTLCache(2**8, 60 * 60)

    def __init__(
        self,
        ar: aioredis.Redis[Any],
        db: DatabaseUtils,
        intents: discord.Intents,
        console_log_level: LogLevel,
    ):
        self.ar = ar
        self.db = db
        self.console_log_level = console_log_level
        self.counter_tasks: set[asyncio.Task] = set()
        self.cleanup_task: asyncio.Task | None = None
        super().__init__(
            intents=intents,
            command_prefix=commands.when_mentioned_or("#"),
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Voice Channels",
            ),
            status=discord.Status.online,
        )
        self.persistent_views_added = False

    def incr_counter(self, cmd_name: str):
        """Increments the counter for a command"""
        self._schedule_counter(cmd_name, 1)

    def incr_role_counter(self, action: str, count: int = 1):
        """
        action: `add` or `remove`.
        Increments the counter for roles added or removed
        """
        self._schedule_counter(f"roles_{action}", count)

    def _schedule_counter(self, name: str, count: int):
        async def increment():
            try:
                await self.ar.hincrby("counters", name, count)
            except Exception as error:
                self.log(
                    LogLevel.ERROR,
                    "Counter update failed",
                    error=error,
                    event="counter_update_failed",
                    counter=name,
                    count=count,
                )

        task = self.loop.create_task(increment())
        self.counter_tasks.add(task)
        task.add_done_callback(self.counter_tasks.discard)

    async def on_ready(self):
        """
        Called when the bot is ready.
        """
        if not self.persistent_views_added:
            self.add_view(Interface(self.db))
            self.persistent_views_added = True

        logger.info(
            "Bot ready",
            extra={
                "event": "bot_ready",
                "context": {
                    "guild_count": len(self.guilds),
                    "shard_count": self.shard_count,
                },
            },
        )
        print(f"Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds.")

        mapping: dict[int, int] = {}
        for guild in self.guilds:
            mapping[guild.shard_id] = mapping.get(guild.shard_id, 0) + 1
        for shard_id, count in mapping.items():
            print(f"Shard {shard_id}: {count}")

        print("------")

    @observed("gateway")
    async def on_shard_disconnect(self, shard_id: int) -> None:
        get_telemetry().gateway("disconnected", shard_id)
        logger.warning(
            "Shard %s disconnected (closing=%s, database_connected=%s)",
            shard_id,
            self.cleanup_task is not None,
            self.db.db.is_connected(),
            extra={
                "event": "shard_disconnected",
                "context": {
                    "shard_id": shard_id,
                    "closing": self.cleanup_task is not None,
                    "database_connected": self.db.db.is_connected(),
                },
            },
        )

    @observed("gateway")
    async def on_shard_ready(self, shard_id: int) -> None:
        get_telemetry().gateway("ready", shard_id)
        logger.info(
            "Shard %s ready with a new session",
            shard_id,
            extra={"event": "shard_ready", "context": {"shard_id": shard_id}},
        )

    @observed("gateway")
    async def on_shard_resumed(self, shard_id: int) -> None:
        get_telemetry().gateway("resumed", shard_id)
        logger.info(
            "Shard %s resumed its existing session",
            shard_id,
            extra={"event": "shard_resumed", "context": {"shard_id": shard_id}},
        )

    async def on_error(self, event_method: str, *args, **kwargs):
        context = {"discord_event": event_method}
        if args and isinstance(args[0], discord.Member):
            member = args[0]
            context.update(
                guild_id=member.guild.id,
                member_id=member.id,
                shard_id=member.guild.shard_id,
            )
        self.log(
            LogLevel.ERROR,
            "Unhandled Discord event error",
            error=sys.exception(),
            event="discord_event_failed",
            **context,
        )

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
        await self.db.delete_generator(channel.guild.id, channel.id)

    async def close(self) -> None:
        if self.cleanup_task is None:
            # Record the caller before starting a task so fatal gateway errors,
            # explicit closes, and context-manager cleanup can be distinguished.
            logger.warning("Bot shutdown requested", stack_info=True)
            self.cleanup_task = asyncio.create_task(self._close_resources())
        await asyncio.shield(self.cleanup_task)

    async def _close_resources(self) -> None:
        try:
            # Cog unload hooks flush work while Discord and the database are usable.
            await super().close()
        finally:
            try:
                await asyncio.gather(*list(self.counter_tasks), return_exceptions=True)
                logger.info("Discord cleanup finished; disconnecting the database")
                await self.db.disconnect()
            finally:
                await self.ar.aclose()
        logger.info("Bot resource cleanup finished")

    async def setup_hook(self) -> None:
        get_telemetry().start_runtime(self)
        configure_gateway_compression()
        logger.info("Connecting to the Prisma query engine")
        await self.db.connect()
        logger.info("Prisma connected; starting Discord gateway connections")

        return await super().setup_hook()

    def log(
        self,
        level: LogLevel,
        message: str,
        *,
        error: BaseException | None = None,
        event: str = "application_log",
        **context,
    ) -> None:
        """Write through the persistent logging handlers immediately."""
        levels = {
            LogLevel.NONE: logging.INFO,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.INFO: logging.INFO,
            LogLevel.DEBUG: logging.DEBUG,
        }
        if error is None and level == LogLevel.ERROR:
            error = sys.exception()
        logging.getLogger("internal.bot").log(
            levels[level],
            message,
            extra={
                "event": event,
                "context": context,
                "console_min_level": logging.CRITICAL + 1
                if self.console_log_level == LogLevel.NONE
                else levels[self.console_log_level],
            },
            exc_info=(type(error), error, error.__traceback__)
            if error is not None
            else None,
        )

    async def on_app_command_completion(
        self,
        interaction: discord.Interaction,
        _command: (
            discord.app_commands.Command[Any, Any, Any]
            | discord.app_commands.ContextMenu
        ),
    ):
        if interaction.guild is None:
            return

        if isinstance(_command, discord.app_commands.Command):
            parent_parent_name = (
                _command.parent.parent.name + "_"
                if _command.parent and _command.parent.parent
                else ""
            )
            parent_name = _command.parent.name + "_" if _command.parent else ""
            command_name = f"{parent_parent_name}{parent_name}{_command.name}"

            self.incr_counter(command_name)

        seen_welcome = await self.ar.hget("seen_welcome", str(interaction.guild.id))
        webhook = await self.ar.hget("webhooks", str(interaction.guild.id))
        if (
            seen_welcome is None
            and webhook is None
            and isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.administrator
        ):
            bot_commands = await self.tree.fetch_commands()
            update_channel_command = list(
                filter(lambda x: x.name == "update_channel", bot_commands)
            )[0]
            embed = discord.Embed(
                title="VC Roles - Welcome",
                description="You haven't set up an update channel yet -> Update channels are a great way to keep up to date with the latest changes to VC Roles. We recommend setting one up now!",
            )
            embed.add_field(
                name="How to set an update channel",
                value=f"Run {update_channel_command.mention} command in the channel you want VC Roles to send updates to.",
            )
            embed.set_thumbnail(
                url=self.user.avatar.url if self.user and self.user.avatar else None
            )
            await interaction.followup.send(embed=embed)
            await self.ar.hset("seen_welcome", str(interaction.guild.id), "1")

    async def send_welcome(self, guild_id: int):
        webhook_url = await self.ar.hget("webhooks", str(guild_id))
        if webhook_url is None:
            return None

        bot_commands = await self.tree.fetch_commands()
        discord_command = list(filter(lambda x: x.name == "discord", bot_commands))[0]
        invite_command = list(filter(lambda x: x.name == "invite", bot_commands))[0]

        async with aiohttp.ClientSession() as session:
            webhook = discord.Webhook.from_url(webhook_url, session=session)
            embed = discord.Embed(
                title="VC Roles",
                description="Welcome to VC Roles! This is the channel where you will receive updates about the bot.",
                colour=0x2F3136,
            )
            embed.add_field(
                name="Commands",
                value="To see a list of commands, visit [our website](https://www.vcroles.com/commands)",
                inline=False,
            )
            embed.add_field(
                name="Support",
                value=f"To join our support server, run {discord_command.mention}",
                inline=False,
            )
            embed.add_field(
                name="Invite",
                value=f"To invite the bot to another server, run {invite_command.mention}",
                inline=False,
            )
            embed.set_thumbnail(
                url=self.user.avatar.url if self.user and self.user.avatar else None,
            )

            await webhook.send(
                embed=embed,
                username="VC Roles Updates",
                avatar_url=(
                    self.user.avatar.url if self.user and self.user.avatar else None
                ),
            )

        return True
