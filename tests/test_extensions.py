import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import discord

from utils.client import VCRolesClient
from utils.types import LogLevel


class ExtensionLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_extensions_load_and_unload_without_leaking_tasks(self):
        cogs = sorted((Path(__file__).resolve().parents[1] / "cogs").glob("*.py"))
        database = Mock(disconnect=AsyncMock())
        redis = Mock(aclose=AsyncMock())
        client = VCRolesClient(redis, database, discord.Intents.none(), LogLevel.ERROR)
        await client._async_setup_hook()
        previous_directory = Path.cwd()
        initial_tasks = asyncio.all_tasks()
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("aiohttp.web.TCPSite.start", new_callable=AsyncMock),
            patch(
                "aiohttp.ClientSession._request",
                side_effect=AssertionError("Network access"),
            ),
            patch.object(client, "log", wraps=client.log) as bot_log,
            self.assertLogs("utils.client", level="INFO"),
        ):
            os.chdir(directory)
            try:
                for path in cogs:
                    await client.load_extension("cogs." + path.stem)
                await client.load_extension("jishaku")
                self.assertEqual(len(client.extensions), len(cogs) + 1)
            finally:
                try:
                    await asyncio.wait_for(client.close(), timeout=15)
                finally:
                    os.chdir(previous_directory)
            self.assertFalse(
                [
                    call
                    for call in bot_log.call_args_list
                    if call.args[0] == LogLevel.ERROR
                ]
            )
        self.assertFalse(client.extensions)
        database.disconnect.assert_awaited_once()
        redis.aclose.assert_awaited_once()
        self.assertFalse(asyncio.all_tasks() - initial_tasks)
