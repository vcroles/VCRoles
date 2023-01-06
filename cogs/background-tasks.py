import datetime as dt

import aiohttp
import discord
from discord.ext import commands, tasks

import config
from utils import LogLevel, VCRolesClient, using_topgg


class BackgroundTasks(commands.Cog):
    def __init__(self, client: VCRolesClient) -> None:
        self.client = client
        self.save_guild_count.start()
        self.reset_limits.start()
        self.log_queue.start()
        self.rotate_log_file.start()
        self.update_topgg.start()

    async def cog_unload(self) -> None:
        self.save_guild_count.cancel()
        self.reset_limits.cancel()
        self.log_queue.cancel()
        self.rotate_log_file.cancel()
        self.update_topgg.cancel()

        return await super().cog_unload()

    @tasks.loop(
        time=[
            dt.time(hour=12, minute=0),
            dt.time(hour=0, minute=0),
            dt.time(hour=6, minute=0),
            dt.time(hour=18, minute=0),
        ]
    )
    async def save_guild_count(self):
        with open("guilds.csv", "a") as f:
            f.write(
                f"{discord.utils.utcnow().strftime('%H:%M %d/%m/%Y')},{len(self.client.guilds)},{self.client.shard_count}\n"
            )

        self.client.log(
            LogLevel.NONE,
            f"Saved guild count: {len(self.client.guilds)}",
        )

    @save_guild_count.before_loop
    async def before_save_guild_count(self):
        await self.client.wait_until_ready()

    @tasks.loop(time=dt.time(hour=0, minute=0))
    async def reset_limits(self):
        await self.client.ar.delete("commands")

        self.client.log(
            LogLevel.INFO,
            "Reset command limits.",
        )

    @reset_limits.before_loop
    async def before_reset_limits(self):
        await self.client.wait_until_ready()

    @tasks.loop(seconds=30)
    async def log_queue(self):
        if self.client.log_queue:
            with open("bot.log", "a") as f:
                f.write("\n" + "\n".join(self.client.log_queue))
                self.client.log_queue.clear()

    @log_queue.before_loop
    async def before_log_queue(self):
        await self.client.wait_until_ready()

    @tasks.loop(time=dt.time(hour=0, minute=0))
    async def rotate_log_file(self):
        with open("bot.log", "r") as f:
            data = f.read()

        with open("bot.old.log", "w") as f:
            f.write(data)

        with open("bot.log", "w") as f:
            f.write("")

    @rotate_log_file.before_loop
    async def before_rotate_log_file(self):
        await self.client.wait_until_ready()

    @tasks.loop(seconds=900)
    async def update_topgg(self):
        if not using_topgg or not config.DBL.TOKEN:
            return

        # for each shard, print how many guilds it's in
        shard_guilds: dict[int, int] = {}
        for guild in self.client.guilds:
            shard_guilds[guild.shard_id] = shard_guilds.get(guild.shard_id, 0) + 1

        async with aiohttp.ClientSession() as session:
            res = await session.post(
                f"https://top.gg/api/bots/{self.client.user.id}/stats",  # type: ignore
                headers={"Authorization": config.DBL.TOKEN},
                json={"server_count": list(shard_guilds.values())},
            )

        if res.status != 200:
            self.client.log(
                LogLevel.ERROR,
                f"Failed to update Top.gg stats: {res.status} {await res.text()!r} ({shard_guilds})",
            )
            return

        self.client.log(
            LogLevel.INFO,
            f"Updated Top.gg stats: {shard_guilds}",
        )

    @update_topgg.before_loop
    async def before_update_topgg(self):
        await self.client.wait_until_ready()


async def setup(client: VCRolesClient):
    await client.add_cog(BackgroundTasks(client))
