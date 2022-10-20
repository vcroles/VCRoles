from typing import Any, Optional

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
        await ctx.channel.send(file=discord.File(f"discord.log"))

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
            self.client.loop.create_task(
                self.client.ar.execute_command("hdel", "commands", str(user_id))  # todo
            )
        else:
            self.client.loop.create_task(
                self.client.ar.execute_command("del", "commands")  # todo
            )
        await ctx.reply("Reset command limit!")


async def setup(client: VCRolesClient):
    await client.add_cog(Dev(client))
