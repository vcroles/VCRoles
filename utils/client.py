import discord
import redis.asyncio as aioredis
from discord.ext import commands

from utils.utils import RedisUtils
from views.interface import Interface


class VCRolesClient(commands.AutoShardedBot):
    def __init__(self, redis: RedisUtils, ar: aioredis.Redis, *args, **kwargs):
        self.redis = redis
        self.ar = ar
        super().__init__(*args, **kwargs)
        self.persistent_views_added = False

    def incr_counter(self, cmd_name: str):
        """Increments the counter for a command"""
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", cmd_name, 1)
        )

    def incr_role_counter(self, action: str, count: int = 1):
        """
        action: `add` or `remove`.
        Increments the counter for roles added or removed
        """
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", f"roles_{action}", count)
        )

    async def on_ready(self):
        """
        Called when the bot is ready.
        """
        if not self.persistent_views_added:
            self.add_view(Interface(self.redis))
            self.persistent_views_added = True

        await self.change_presence(status=discord.Status.online)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="Voice Channels"
            )
        )

        print(f"Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds.")
        print("------")

    async def on_guild_join(self, guild: discord.Guild):
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", "guilds_join", 1)
        )

    async def on_guild_remove(self, guild: discord.Guild):
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", "guilds_leave", 1)
        )
        self.redis.guild_remove(guild.id)

    async def on_command_error(self, ctx, error):
        return  # who cares about errors

    async def on_error(self, event, *args, **kwargs):
        # the seemingly pointless error handler
        with open("error.log", "a") as f:
            f.write(
                f"{discord.utils.utcnow().strftime('%m/%d/%Y, %H:%M:%S')} {event}: {str(args).encode('utf-8')=}: {str(kwargs).encode('utf-8')=}\n"
            )

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """
        When a channel is deleted, remove it from the redis database.
        """
        # Voice Channels
        if isinstance(channel, discord.VoiceChannel):
            data = self.redis.get_linked("voice", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("voice", channel.guild.id, data)

            data = self.redis.get_linked("permanent", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("permanent", channel.guild.id, data)

            data = self.redis.get_linked("all", channel.guild.id)
            if str(channel.id) in data["except"]:
                data["except"].remove(str(channel.id))
                self.redis.update_linked("all", channel.guild.id, data)

        # Stage Channels
        if isinstance(channel, discord.StageChannel):
            data = self.redis.get_linked("stage", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("stage", channel.guild.id, data)

        # Category Channels
        if isinstance(channel, discord.CategoryChannel):
            data = self.redis.get_linked("category", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("category", channel.guild.id, data)

    async def send_reminder(self):
        guild = await self.fetch_guild(775477268893270027)
        for hook in await guild.webhooks():
            if hook.channel.id == 869494079745056808 and hook.token:
                embed = discord.Embed(
                    title="Vote for VC Roles Here",
                    description="Vote & get unlimited command usage!\nhttps://top.gg/bot/775025797034541107/vote/",
                    color=discord.Color.blue(),
                    url="https://top.gg/bot/775025797034541107/vote/",
                )
                await hook.send(
                    embeds=[embed],
                    username="VC Roles Top.gg",
                    avatar_url="https://avatars.githubusercontent.com/u/34552786",
                )
