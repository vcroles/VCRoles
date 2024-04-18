from __future__ import annotations

import datetime
from typing import Any, Optional
from asyncache import cached  # type: ignore
from cachetools import TTLCache

import aiohttp
import discord
import redis.asyncio as aioredis
from discord.ext import commands

import config
from utils.database import DatabaseUtils
from utils.types import LogLevel, using_topgg
from views.interface import Interface


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
        self.log_queue: list[str] = []
        self.console_log_level = console_log_level
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

    def incr_analytics_counter(self, guild_id: int, item: str, count: int = 1):
        """Increments the counter for an analytics item"""
        self.loop.create_task(
            self.ar.hincrby(f"guild:{guild_id}:analytics", item, count)
        )
        self.loop.create_task(
            self.ar.hincrby(
                f"guild:{guild_id}:analytics",
                f"{item}-{datetime.datetime.now(datetime.UTC).strftime('%H')}",
                count,
            )
        )

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

        guild = await self.db.get_guild_data(interaction.guild.id)
        valid_premium = await self.check_premium_guild(interaction.guild.id)
        if (guild.premium or valid_premium) and guild.analytics:
            self.incr_analytics_counter(interaction.guild.id, "commands_used")

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
                name="Premium",
                value='To get premium, click "Upgrade" on the bot\'s profile.',
                inline=False,
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

    @cached(entitlements_cache)
    async def check_premium_guild(self, guild_id: int | None) -> bool:
        if not guild_id:
            return False

        valid_premium = any(
            [
                entitlement.is_expired() is False and entitlement.guild_id == guild_id
                async for entitlement in self.entitlements()
            ]
        )

        return valid_premium
