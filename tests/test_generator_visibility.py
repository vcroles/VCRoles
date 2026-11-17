import asyncio
import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
from prisma.enums import LinkType

from utils.generator import GeneratorUtils
from voicestate.generator import Generator


class GeneratorVisibilityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.guild = Mock(id=1)
        self.channel = discord.VoiceChannel(
            state=Mock(),
            guild=self.guild,
            data={
                "id": "10",
                "name": "___hidden___",
                "position": 0,
                "parent_id": "20",
                "bitrate": 64000,
                "user_limit": 0,
                "flags": 1 << 17,
                "permission_overwrites": [],
            },
        )
        self.guild.get_role.return_value = None
        self.member = Mock(id=3, guild=self.guild)
        self.member.voice = SimpleNamespace(channel=self.channel)
        self.db = Mock()
        self.db.get_generators = AsyncMock(
            return_value=[SimpleNamespace(categoryId="20", generatorId="2")]
        )
        self.record = SimpleNamespace(
            userEditable=True,
            VoiceGenerator=SimpleNamespace(defaultRole=None, defaultOptions=[]),
        )
        self.db.get_generated_channel = AsyncMock(return_value=self.record)
        self.db.update_generated_channel = AsyncMock()
        self.utils = GeneratorUtils(self.db)

    def visible(self):
        self.channel._flags = 0
        self.channel.name = "Generated channel"

    async def test_hidden_channel_rejects_all_controls_before_database_or_http(self):
        calls = [
            ("lock", ()),
            ("unlock", ()),
            ("hide", ()),
            ("unhide", ()),
            ("increase_limit", ()),
            ("decrease_limit", ()),
            ("set_limit", (2,)),
            ("rename", ("New name",)),
            ("restrict", ([],)),
            ("permit", ([],)),
            ("claim", ()),
        ]
        for method, args in calls:
            with self.subTest(method=method):
                result = await getattr(self.utils, method)(self.member, *args)
                self.assertIn("cannot view", result)
        self.db.get_generators.assert_not_awaited()
        self.db.get_generated_channel.assert_not_awaited()
        self.db.update_generated_channel.assert_not_awaited()

    async def test_visibility_lost_during_database_read_prevents_overwrite_edit(self):
        self.visible()

        async def configuration(*args):
            self.channel._flags = 1 << 17
            return self.record

        self.db.get_generated_channel.side_effect = configuration
        self.assertIn("cannot view", await self.utils.hide(self.member))
        self.channel._state.http.edit_channel.assert_not_called()

    async def test_visible_channels_still_use_retained_category_id(self):
        self.visible()
        # Membership in the configured category uses parent_id rather than
        # requiring a full cached CategoryChannel object.
        self.guild.get_channel.return_value = None
        self.assertTrue(await self.utils.in_voice_channel(self.member))

    async def test_visible_hide_preserves_existing_overwrites(self):
        self.visible()
        channel = Mock(spec=discord.VoiceChannel, id=10, category_id=20)
        channel.is_obfuscated.return_value = False
        other_role = discord.Object(id=99)
        channel.overwrites = {other_role: discord.PermissionOverwrite(connect=False)}
        channel.edit = AsyncMock()
        self.member.voice.channel = channel
        self.assertEqual(await self.utils.hide(self.member), "Hidden voice channel!")
        overwrites = channel.edit.await_args.kwargs["overwrites"]
        self.assertFalse(overwrites[other_role].connect)
        self.assertFalse(overwrites[self.guild.default_role].view_channel)

    async def test_cog_resets_observations_only_on_visibility_transition(self):
        voice = importlib.import_module("cogs.voicestate")
        cog = object.__new__(voice.VoiceState)
        cog.generator = Mock()
        before = Mock(is_obfuscated=Mock(return_value=True))
        after = Mock(is_obfuscated=Mock(return_value=False))
        await cog.on_guild_channel_update(before, after)
        cog.generator.channel_visibility_changed.assert_called_once_with(after)
        cog.generator.reset_mock()
        before.is_obfuscated.return_value = False
        await cog.on_guild_channel_update(before, after)
        cog.generator.channel_visibility_changed.assert_not_called()

    async def test_id_based_role_linking_still_runs_for_an_obfuscated_channel(self):
        voice = importlib.import_module("cogs.voicestate")
        cog = object.__new__(voice.VoiceState)
        cog.client = Mock(db=self.db, loop=asyncio.get_running_loop())
        cog.member_queues = {}
        cog.generator = Generator(cog.client)
        role = Mock(spec=discord.Role, id=99)
        role.is_assignable.return_value = True
        self.guild.get_role.return_value = role
        self.guild.get_channel.return_value = SimpleNamespace(id=20)
        self.member.display_name = "Member"
        self.db.get_all_linked_channel = AsyncMock(
            return_value=[
                SimpleNamespace(
                    excludeChannels=[],
                    linkedRoles=["99"],
                    reverseLinkedRoles=[],
                    type=LinkType.REGULAR,
                    suffix=None,
                )
            ]
        )
        _, failed = await cog.join(self.member, SimpleNamespace(channel=self.channel))
        self.assertEqual(failed, [])
        self.db.get_all_linked_channel.assert_awaited_once_with(1, 10, 20)
        self.assertEqual(cog.member_queues[1][0].to_add, [role])
        self.db.get_generated_channel.assert_not_awaited()
