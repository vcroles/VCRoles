import datetime as dt

import discord
from discord.ext import commands, tasks
from utils.client import VCRolesClient


class Premium(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.premium_check.start()

    async def cog_unload(self):
        self.premium_check.cancel()

        return await super().cog_unload()

    @tasks.loop(time=[dt.time(hour=0, minute=0)])
    async def premium_check(self):
        """Check if premium subscriptions have expired"""

        async_entitlements = self.client.entitlements()
        entitlements: list[discord.Entitlement] = []

        async for ent in async_entitlements:
            entitlements.append(ent)

        valid_entitlements: list[discord.Entitlement] = []
        invalid_entitlements: list[discord.Entitlement] = []
        for ent in entitlements:
            if ent.is_expired() is False:
                valid_entitlements.append(ent)
            else:
                invalid_entitlements.append(ent)

        for ent in invalid_entitlements:
            await self.client.ar.hset("premium", str(ent.user_id), 0)

        for ent in valid_entitlements:
            await self.client.ar.hset("premium", str(ent.user_id), 1)

    @premium_check.before_loop
    async def before_premium_check(self):
        await self.client.wait_until_ready()

    @commands.Cog.listener()
    async def on_entitlement_create(self, entitlement: discord.Entitlement):
        # Set the premium status of the user
        await self.client.ar.hset("premium", str(entitlement.user_id), 1)

    @commands.Cog.listener()
    async def on_entitlement_update(self, entitlement: discord.Entitlement):
        # Set the premium status of the user as required
        if entitlement.is_expired() is False:
            await self.client.ar.hset("premium", str(entitlement.user_id), 1)


async def setup(client: VCRolesClient):
    await client.add_cog(Premium(client))
