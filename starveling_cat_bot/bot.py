import asyncio
import logging
from aiohttp import web

from starveling_cat_bot.discord_client import DiscordClient

_log = logging.getLogger(__name__)


class Bot:

    def _init_aio(self):
        self.aio_app = web.Application()
        self.aio_app.router.add_post("/github-payload", self.handle_payload)
        self.aio_runner = web.AppRunner(self.aio_app)
        self.site = None

    def _init_discord(self):
        self.discord_client = DiscordClient()

    def __init__(self, config):
        self.config = config
        self.aio_interface = config["interface"]
        self.aio_port = config["port"]

        self.github_secret = config["github_secret"]
        self.discord_secret = config["discord_secret"]
        self._init_aio()
        self._init_discord()

        self.discord_task = None

    async def setup(self):
        await self.aio_runner.setup()
        self.site = web.TCPSite(self.aio_runner, self.aio_interface, self.aio_port)

    async def start(self):
        await self.site.start()
        # Эта дрянь не отпускает луп, если её эвейтить прямо сразу
        self.discord_task = asyncio.create_task(self.discord_client.start(self.discord_secret))
        _log.info("Everything started")

    async def shutdown(self):
        await self.discord_client.close()
        await self.discord_task
        await self.aio_runner.cleanup()

    async def handle_payload(self, request) -> web.Response:
        data = await request.json()
        _log.info("got push payload: %s", data)
        await self.discord_client.process_push_hook(data)
        return web.Response()
