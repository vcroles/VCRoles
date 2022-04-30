from typing import Optional

import discord
from discord.ext import commands

from bot import MyClient


class Dev(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def shards(self, ctx):
        shard_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Sharding Info:",
            description=f"There are {len(self.client.shards)} shards.\nThis is shard {ctx.guild.shard_id} - latency: {round(self.client.latency * 1000)} ms",
        )
        await ctx.send(embed=shard_embed)

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def remind(self, ctx):
        await self.client.send_reminder()
        await ctx.send("Reminder sent")

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def logs(self, ctx):
        await ctx.send("Fetching Logs...")
        await ctx.channel.send(file=discord.File(f"discord.log"))
        await ctx.channel.send(file=discord.File(f"error.log"))

    @commands.command(aliases=["sync"])
    @commands.is_owner()
    async def sync_commands(
        self, ctx: commands.Context, guild_id: Optional[int] = None
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
    async def reset_limit(self, ctx: commands.Context, user_id: int = None):
        if user_id:
            self.client.loop.create_task(
                self.client.ar.execute_command("hdel", "commands", str(user_id))
            )
        else:
            self.client.loop.create_task(
                self.client.ar.execute_command("del", "commands")
            )
        await ctx.reply("Reset command limit!")


async def setup(client: MyClient):
    await client.add_cog(Dev(client))
