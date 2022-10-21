import datetime as dt
import json

import discord
from discord.ext import commands, tasks

from utils import VCRolesClient


class BackgroundTasks(commands.Cog):
    def __init__(self, client: VCRolesClient) -> None:
        self.client = client
        self.save_guild_count.start()
        self.reset_limits.start()

    async def cog_unload(self) -> None:
        self.save_guild_count.cancel()
        self.reset_limits.cancel()

        return await super().cog_unload()

    @tasks.loop(time=[dt.time(hour=12, minute=0), dt.time(hour=0, minute=0)])
    async def save_guild_count(self):
        with open("guilds.json", "r") as f:
            data = json.load(f)

        data[discord.utils.utcnow().strftime("%H:%M %d/%m/%Y")] = len(
            self.client.guilds
        )

        with open("guilds.json", "w") as f:
            json.dump(data, f)

    @save_guild_count.before_loop
    async def before_save_guild_count(self):
        await self.client.wait_until_ready()

    @tasks.loop(time=dt.time(hour=0, minute=0))
    async def reset_limits(self):
        await self.client.ar.delete("commands")

    @reset_limits.before_loop
    async def before_reset_limits(self):
        await self.client.wait_until_ready()


async def setup(client: VCRolesClient):
    await client.add_cog(BackgroundTasks(client))
