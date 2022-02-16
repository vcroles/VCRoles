import discord
from discord.ext import commands, tasks

from bot import MyClient


class SyncCommands(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client
        self.synccommands.start()

    @tasks.loop(seconds=30)
    async def synccommands(self):
        await self.client.register_commands()
        print("Commands registered successfully!")

    @synccommands.before_loop
    async def before_sync(self):
        await self.client.wait_until_ready()


def setup(client: MyClient):
    client.add_cog(SyncCommands(client))
