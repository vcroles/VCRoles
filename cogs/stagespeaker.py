import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner
from utils.utils import handle_data_deletion


class StageSpeaker(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    stage_commands = app_commands.Group(
        name="stage", description="Stage channel commands"
    )
    speaker_commands = app_commands.Group(
        name="speaker", description="Stage speaker commands", parent=stage_commands
    )

    @speaker_commands.command()
    @app_commands.describe(
        channel="Select a channel to link", role="Select a role to link"
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def link(
        self,
        interaction: discord.Interaction,
        channel: discord.StageChannel,
        role: discord.Role,
    ):
        """Link a stage channel speaker to a role"""
        pass


async def setup(client: MyClient):
    await client.add_cog(StageSpeaker(client))
