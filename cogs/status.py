from aiohttp import web
from discord.ext import commands

from config import WEBSERVER_PORT
from utils.client import VCRolesClient

app = web.Application()
routes = web.RouteTableDef()


class Status(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

        @routes.get("/status")
        async def status(request):  # type: ignore
            if self.client.is_ready() is False:
                return web.Response(status=503)
            return web.Response(status=200, text="OK")

        self.webserver_port = WEBSERVER_PORT
        app.add_routes(routes)

    async def cog_load(self) -> None:
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=self.webserver_port)
        await site.start()

        return await super().cog_load()


async def setup(client: VCRolesClient):
    await client.add_cog(Status(client))
