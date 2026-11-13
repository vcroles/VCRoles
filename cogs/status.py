from aiohttp import web
from discord.ext import commands

from config import WEBSERVER_PORT
from utils.client import VCRolesClient


class Status(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.app = web.Application()
        self.runner = web.AppRunner(self.app)

        async def status(request):
            if self.client.is_ready() is False:
                return web.Response(status=503)
            return web.Response(status=200, text="OK")

        self.webserver_port = WEBSERVER_PORT
        self.app.router.add_get("/status", status)

    async def cog_load(self) -> None:
        try:
            await self.runner.setup()
            site = web.TCPSite(self.runner, host="0.0.0.0", port=self.webserver_port)
            await site.start()
        except BaseException:
            await self.runner.cleanup()
            raise

        return await super().cog_load()

    async def cog_unload(self) -> None:
        await self.runner.cleanup()
        await super().cog_unload()


async def setup(client: VCRolesClient):
    await client.add_cog(Status(client))
