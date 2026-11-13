import asyncio
import unittest
import zlib
from unittest.mock import AsyncMock, Mock, patch

import discord
import discord.utils
import yarl
from discord.gateway import DiscordWebSocket

from utils.client import VCRolesClient
from utils.gateway import ZlibDecompressionContext, configure_gateway_compression
from utils.types import LogLevel


class GatewayCompressionTests(unittest.IsolatedAsyncioTestCase):
    def test_stream_preserves_history_and_buffers_split_flush_marker(self):
        compressor = zlib.compressobj()
        decoder = ZlibDecompressionContext()
        for message in ('{"op":10,"d":{}}', '{"content":"café"}'):
            compressed = compressor.compress(message.encode()) + compressor.flush(
                zlib.Z_SYNC_FLUSH
            )
            self.assertIsNone(decoder.decompress(compressed[:-2]))
            self.assertEqual(decoder.decompress(compressed[-2:]), message)

    def test_each_websocket_has_independent_compression_history(self):
        decoders = [ZlibDecompressionContext(), ZlibDecompressionContext()]
        compressors = [zlib.compressobj(), zlib.compressobj()]
        for index in (0, 1, 0, 1):
            message = f'{{"shard":{index}}}'
            compressed = compressors[index].compress(message.encode())
            compressed += compressors[index].flush(zlib.Z_SYNC_FLUSH)
            self.assertEqual(decoders[index].decompress(compressed), message)

    async def test_library_requests_zlib_and_uses_matching_decoder(self):
        client = VCRolesClient(Mock(), Mock(), discord.Intents.none(), LogLevel.ERROR)
        socket = Mock()
        client.http.ws_connect = AsyncMock(return_value=socket)
        original = discord.utils._ActiveDecompressionContext
        try:
            configure_gateway_compression()
            await client._async_setup_hook()
            with (
                patch.object(DiscordWebSocket, "poll_event", new_callable=AsyncMock),
                patch.object(DiscordWebSocket, "identify", new_callable=AsyncMock),
                patch.object(DiscordWebSocket, "resume", new_callable=AsyncMock),
            ):
                for resume in (False, True):
                    ws = await DiscordWebSocket.from_client(
                        client,
                        gateway=yarl.URL("wss://gateway.discord.gg/"),
                        shard_id=0,
                        resume=resume,
                    )
                    url = yarl.URL(client.http.ws_connect.call_args.args[0])
                    self.assertEqual(url.query["compress"], "zlib-stream")
                    self.assertIsInstance(ws._decompressor, ZlibDecompressionContext)
                    compressor = zlib.compressobj()
                    payload = compressor.compress(b'{"op":11,"d":null}')
                    payload += compressor.flush(zlib.Z_SYNC_FLUSH)
                    await ws.received_message(payload)
        finally:
            discord.utils._ActiveDecompressionContext = original
            await client.http.close()


class ClientLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_close_keeps_database_until_discord_cleanup_finishes(self):
        database = Mock(connect=AsyncMock(), disconnect=AsyncMock())
        redis = Mock(aclose=AsyncMock())
        client = VCRolesClient(redis, database, discord.Intents.none(), LogLevel.ERROR)

        async def close_discord():
            database.disconnect.assert_not_awaited()
            redis.aclose.assert_not_awaited()
            await asyncio.sleep(0)
            database.disconnect.assert_not_awaited()

        with (
            patch(
                "discord.ext.commands.AutoShardedBot.close",
                new=AsyncMock(side_effect=close_discord),
            ) as close,
            self.assertLogs("utils.client", level="INFO"),
        ):
            await asyncio.gather(client.close(), client.close())
            await client.close()
            close.assert_awaited_once()
            database.disconnect.assert_awaited_once()
            redis.aclose.assert_awaited_once()

    async def test_shard_disconnect_does_not_close_database_or_bot(self):
        database = Mock(disconnect=AsyncMock())
        redis = Mock(aclose=AsyncMock())
        client = VCRolesClient(redis, database, discord.Intents.none(), LogLevel.ERROR)
        with self.assertLogs("utils.client", level="WARNING"):
            await client.on_shard_disconnect(5)
        self.assertIsNone(client.cleanup_task)
        database.disconnect.assert_not_awaited()
        redis.aclose.assert_not_awaited()
