from typing import Any, Literal, Optional

import discord
from discord.ext import commands

from utils.client import VCRolesClient


class Dev(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def shards(self, ctx: commands.Context[Any]):
        if not ctx.guild:
            return await ctx.send("You must use this command in a guild.")
        shard_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Sharding Info:",
            description=f"There are {len(self.client.shards)} shards.\nThis is shard {ctx.guild.shard_id} - latency: {round(self.client.latency * 1000)} ms",
        )
        await ctx.send(embed=shard_embed)

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


async def setup(client: VCRolesClient):
    await client.add_cog(Dev(client))
