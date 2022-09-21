from aiohttp import web
from discord.ext import commands, tasks

from utils.client import VCRolesClient

app = web.Application()
routes = web.RouteTableDef()


class Status(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.web_server.start()

        @routes.get("/status")
        async def status(request):
            return web.Response(status=200, text="OK")

        self.webserver_port = 5000
        app.add_routes(routes)

    @tasks.loop()
    async def web_server(self):
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=self.webserver_port)
        await site.start()

    @web_server.before_loop
    async def before_web_server(self):
        await self.client.wait_until_ready()


async def setup(client: VCRolesClient):
    await client.add_cog(Status(client))
