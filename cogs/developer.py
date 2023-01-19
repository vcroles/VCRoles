from typing import Annotated, Any, Literal, Optional

import aiohttp
import discord
from discord.ext import commands

from utils.client import VCRolesClient
from utils.types import LogLevel


class Dev(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def logs(self, ctx: commands.Context[Any]):
        await ctx.send("Fetching Logs...")
        await ctx.channel.send(file=discord.File("discord.log"))

    @commands.command(aliases=["sync"])
    @commands.is_owner()
    async def sync_commands(
        self, ctx: commands.Context[Any], guild_id: Optional[int] = None
    ):
        await ctx.reply("Syncing commands...")
        if guild_id:
            guild = discord.Object(id=guild_id)
            self.client.tree.copy_global_to(guild=guild)
            await self.client.tree.sync(guild=guild)
        else:
            await self.client.tree.sync()
        await ctx.send("Done!")

    @commands.command(aliases=["reset"])
    @commands.is_owner()
    async def reset_limit(
        self, ctx: commands.Context[Any], user_id: Optional[int] = None
    ):
        if user_id:
            self.client.loop.create_task(self.client.ar.hdel("commands", str(user_id)))
        else:
            self.client.loop.create_task(self.client.ar.delete("commands"))
        await ctx.reply("Reset command limit!")

    @commands.command(aliases=["pg"])
    @commands.is_owner()
    async def premium_guild(
        self, ctx: commands.Context[Any], guild_id: int, enabled: bool = True
    ):
        res = await self.client.db.db.guild.update(
            where={"id": str(guild_id)}, data={"premium": enabled}
        )
        if not res:
            await ctx.send(f"Unknown guild ID - {guild_id}")
        else:
            await ctx.send(
                f"{'Enabled' if enabled else 'Disabled'} premium in guild {guild_id}"
            )

    @commands.command(aliases=["pu"])
    @commands.is_owner()
    async def premium_user(
        self, ctx: commands.Context[Any], user_id: int, enabled: bool = True
    ):
        await self.client.ar.hset("premium", str(user_id), int(enabled))

        await ctx.send(
            f"{'Enabled' if enabled else 'Disabled'} premium for user {user_id}"
        )

    @commands.command()
    @commands.is_owner()
    async def status(
        self,
        ctx: commands.Context[Any],
        status_type: Literal["playing", "streaming", "listening", "watching"],
        *,
        status_text: str,
    ):
        if status_type == "playing":
            activity_type = discord.ActivityType.playing
        elif status_type == "streaming":
            activity_type = discord.ActivityType.streaming
        elif status_type == "listening":
            activity_type = discord.ActivityType.listening
        elif status_type == "watching":
            activity_type = discord.ActivityType.watching
        else:
            activity_type = discord.ActivityType.watching

        await self.client.change_presence(
            activity=discord.Activity(type=activity_type, name=status_text)
        )

        await ctx.send("Successfully edited status.")

    @commands.command(aliases=["ll"])
    @commands.is_owner()
    async def loglevel(
        self,
        ctx: commands.Context[Any],
        level: Annotated[LogLevel, LogLevel.from_string],
    ):
        self.client.console_log_level = level
        await ctx.send(f"Set log level to {level.name}")

    @commands.command(aliases=["su"])
    @commands.is_owner()
    async def send_update_message(
        self, ctx: commands.Context[Any], guilds: str, *, message: str
    ):
        webhooks = await self.client.ar.hgetall("webhooks") or {}

        bot_commands = await self.client.tree.fetch_commands()
        discord_command = list(filter(lambda x: x.name == "discord", bot_commands))[0]
        invite_command = list(filter(lambda x: x.name == "invite", bot_commands))[0]

        embed = discord.Embed(
            title="VC Roles",
            description=message,
            colour=0x2F3136,
        )
        embed.add_field(
            name="Premium",
            value="To get premium, visit [our premium page](https://premium.vcroles.com/l/vcroles)",
            inline=False,
        )
        embed.add_field(
            name="Support",
            value=f"To join our support server, run {discord_command.mention}",
        )
        embed.add_field(
            name="Invite",
            value=f"To invite the bot to another server, run {invite_command.mention}",
        )
        embed.set_thumbnail(
            url=self.client.user.avatar.url
            if self.client.user and self.client.user.avatar
            else None,
        )

        if guilds == "all":
            async with aiohttp.ClientSession() as session:
                for url in webhooks.values():
                    try:
                        webhook = discord.Webhook.from_url(url, session=session)
                        await webhook.send(
                            embed=embed,
                            username="VC Roles Updates",
                            avatar_url=self.client.user.avatar.url
                            if self.client.user and self.client.user.avatar
                            else None,
                        )
                    except:
                        pass
        else:
            async with aiohttp.ClientSession() as session:
                for guild in guilds.split(","):
                    if guild not in webhooks:
                        continue
                    try:
                        webhook = discord.Webhook.from_url(
                            str(webhooks.get(guild)), session=session
                        )
                        await webhook.send(
                            embed=embed,
                            username="VC Roles Updates",
                            avatar_url=self.client.user.avatar.url
                            if self.client.user and self.client.user.avatar
                            else None,
                        )
                    except:
                        pass

        await ctx.send("Sent update message!")


async def setup(client: VCRolesClient):
    await client.add_cog(Dev(client))
