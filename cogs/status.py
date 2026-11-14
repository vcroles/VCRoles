import logging

from aiohttp import web
from discord.ext import commands

from config import WEBSERVER_PORT
from utils.client import VCRolesClient
from utils.telemetry import get_telemetry


class Status(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.app = web.Application()
        self.runner = web.AppRunner(self.app)
        self.last_status: int | None = None

        async def status(request):
            code = 200 if self.client.is_ready() else 503
            get_telemetry().health(code)
            if code != self.last_status:
                logging.getLogger(__name__).log(
                    logging.INFO if code == 200 else logging.WARNING,
                    "Health endpoint status changed to %s",
                    code,
                    extra={
                        "event": "health_status_changed",
                        "context": {
                            "status": code,
                            "previous_status": self.last_status,
                        },
                    },
                )
                self.last_status = code
            if code == 503:
                return web.Response(status=code)
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
