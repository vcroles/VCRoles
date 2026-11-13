import asyncio
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord

VCControl = importlib.import_module("cogs.vc-control").VCControl


class VoiceControlTests(unittest.IsolatedAsyncioTestCase):
    def make_interaction(self, in_voice=True):
        member = Mock(spec=discord.Member)
        member.id = 1
        member.voice = SimpleNamespace(
            channel=SimpleNamespace(mention="#voice") if in_voice else None
        )
        return SimpleNamespace(
            guild=Mock(),
            user=member,
            guild_id=123,
            channel_id=456,
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    async def test_all_controls_acknowledge_before_fetching_and_reply_after_edits(self):
        for name in ("mute", "unmute", "deafen", "undeafen"):
            with self.subTest(command=name):
                interaction = self.make_interaction()
                member = Mock(id=2)

                async def edit(interaction=interaction, **kwargs):
                    interaction.response.defer.assert_awaited_once_with(thinking=True)
                    interaction.followup.send.assert_not_awaited()

                member.edit = AsyncMock(side_effect=edit)
                cog = VCControl(Mock(loop=asyncio.get_running_loop()))

                async def get_members(*args, interaction=interaction, member=member):
                    interaction.response.defer.assert_awaited_once_with(thinking=True)
                    return [member]

                cog.get_members = AsyncMock(side_effect=get_members)
                await getattr(VCControl, name).callback(cog, interaction)
                member.edit.assert_awaited_once()
                interaction.followup.send.assert_awaited_once()
                interaction.response.send_message.assert_not_awaited()

    async def test_controls_reject_missing_channel_without_fetching_members(self):
        for name in ("mute", "unmute", "deafen", "undeafen"):
            with self.subTest(command=name):
                interaction = self.make_interaction(in_voice=False)
                cog = VCControl(Mock())
                cog.get_members = AsyncMock()
                await getattr(VCControl, name).callback(cog, interaction)
                interaction.response.send_message.assert_awaited_once()
                interaction.response.defer.assert_not_awaited()
                cog.get_members.assert_not_awaited()

    async def test_edit_failure_does_not_report_success(self):
        interaction = self.make_interaction()
        cog = VCControl(Mock(loop=asyncio.get_running_loop()))
        cog.get_members = AsyncMock(
            return_value=[Mock(edit=AsyncMock(side_effect=RuntimeError("failed")))]
        )
        with self.assertRaises(RuntimeError):
            await VCControl.unmute.callback(cog, interaction)
        interaction.response.defer.assert_awaited_once()
        interaction.followup.send.assert_not_awaited()
