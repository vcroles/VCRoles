"""Gateway compression workaround for the pinned discord.py fork."""

import logging
import zlib

import discord.utils


class ZlibDecompressionContext:
    """One streaming decoder per websocket, including fragmented messages."""

    COMPRESSION_TYPE = "zlib-stream"

    def __init__(self) -> None:
        self.context = zlib.decompressobj()
        self.buffer = bytearray()

    def decompress(self, data: bytes, /) -> str | None:
        self.buffer.extend(data)
        if not self.buffer.endswith(b"\x00\x00\xff\xff"):
            return None

        message = self.context.decompress(self.buffer)
        self.buffer.clear()
        return message.decode("utf-8")


def configure_gateway_compression() -> None:
    # The fork automatically selects zstd when the speed extra is installed.
    # Production has exited on uncaught ZstdError while decoding gateway frames.
    # There is no public compression selector in this pinned version: replace
    # its factory so both the requested protocol and every decoder use zlib.
    # Keep the gateway integration test when updating the discord.py dependency.
    discord.utils._ActiveDecompressionContext = ZlibDecompressionContext
    logging.getLogger(__name__).info("Discord gateway compression: zlib-stream")
