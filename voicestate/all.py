import discord

class all():

    def __init__(self, client: discord.AutoShardedBot):
        self.client = client

    async def join(self) -> int:
        return 1

    async def leave(self):
        pass

    async def change(self):
        pass