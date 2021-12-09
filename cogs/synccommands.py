import discord
from discord.ext import commands, tasks
from bot import MyClient


class syncCommands(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client
        self.synccommands.start()

    @tasks.loop(seconds=15)
    async def synccommands(self):
        await self.client.register_commands()
        print("Commands registered successfully!")

    @synccommands.before_loop
    async def before_sync(self):
        await self.client.wait_until_ready()


def setup(client):
    client.add_cog(syncCommands(client))
