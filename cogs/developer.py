from typing import Annotated, Any, Literal, Optional

import aiohttp
import discord
from discord.enums import EntitlementOwnerType
from discord.ext import commands

from utils.client import VCRolesClient
from utils.types import LogLevel


class Dev(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def create_entitlement(
        self, ctx: commands.Context[Any], sku_id: int, guild: discord.Guild
    ):
        skus = await self.client.fetch_skus()
        sku = None
        for s in skus:
            if s.id == sku_id:
                sku = s
                break

        if not sku:
            return await ctx.send("Sku not found")

        await self.client.create_entitlement(sku, guild, EntitlementOwnerType.guild)

        entitlements = self.client.entitlements(guild=guild)
        entitlement = None
        async for ent in entitlements:
            if ent.guild_id == guild.id:
                entitlement = ent
                break

        if not entitlement:
            return await ctx.send("Unable to create entitlement.")

        await ctx.send(
            f"Created entitlement for {guild.name}. ID: {entitlement.id} | Type: {entitlement.type} | Expired: {entitlement.is_expired()}"
        )

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def remove_entitlement(self, ctx: commands.Context[Any], entitlement_id: int):
        entitlements = self.client.entitlements(guild=ctx.guild)
        entitlement = None
        async for ent in entitlements:
            if ent.id == entitlement_id:
                entitlement = ent
                break

        if not entitlement:
            return await ctx.send("Entitlement not found.")

        guild = entitlement.guild
        user = entitlement.user

        try:
            await entitlement.delete()
        except Exception as e:
            return await ctx.send(f"Unable to delete entitlement. Error: {e}")

        await ctx.send(
            f"Removed entitlement for {guild.name if guild else 'Unknown Guild'} ({user.name if user else 'Unknown User'}). ID: {entitlement.id} | Type: {entitlement.type}"
        )

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def list_entitlements(self, ctx: commands.Context[Any]):
        async_entitlements = self.client.entitlements()

        entitlements: list[discord.Entitlement] = []
        async for ent in async_entitlements:
            entitlements.append(ent)

        if not entitlements:
            return await ctx.send("No entitlements found.")

        await ctx.send(
            f"Entitlements:\n"
            + "\n".join(
                [
                    f"Guild: {ent.guild_id} | User: {ent.user_id} | ID: {ent.id} | Type: {ent.type} | Expired: {ent.is_expired()} | SKU: {ent.sku_id}"
                    for ent in entitlements
                ]
            )
        )

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
            value='To get premium, click "Upgrade" on the bot\'s profile.',
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
            url=(
                self.client.user.avatar.url
                if self.client.user and self.client.user.avatar
                else None
            ),
        )

        if guilds == "all":
            async with aiohttp.ClientSession() as session:
                for url in webhooks.values():
                    try:
                        webhook = discord.Webhook.from_url(url, session=session)
                        await webhook.send(
                            embed=embed,
                            username="VC Roles Updates",
                            avatar_url=(
                                self.client.user.avatar.url
                                if self.client.user and self.client.user.avatar
                                else None
                            ),
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
                            avatar_url=(
                                self.client.user.avatar.url
                                if self.client.user and self.client.user.avatar
                                else None
                            ),
                        )
                    except:
                        pass

        await ctx.send("Sent update message!")


async def setup(client: VCRolesClient):
    await client.add_cog(Dev(client))
