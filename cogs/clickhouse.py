import clickhouse_connect
import discord
from discord.ext import commands

from utils.client import VCRolesClient


class ClickHouse(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client


async def setup(client: VCRolesClient):
    await client.add_cog(ClickHouse(client))
