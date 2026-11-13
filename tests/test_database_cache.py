import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from cachetools.keys import hashkey

from utils.database import DatabaseUtils


class GeneratorCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.database = DatabaseUtils()
        for cache in (
            self.database.generator_cache,
            self.database.get_generators_cache,
            self.database.generated_channel_cache,
        ):
            cache.clear()
            self.addCleanup(cache.clear)

    def test_invalidates_both_string_and_integer_ids_without_affecting_other_guilds(
        self,
    ):
        database = self.database
        for guild_id, generator_id in ((1, 2), ("1", "2"), (3, 4)):
            database.generator_cache[hashkey(database, guild_id, generator_id)] = True
            database.get_generators_cache[hashkey(database, guild_id)] = True
        database.invalidate_generator("1", 2)
        self.assertEqual(list(database.generator_cache), [hashkey(database, 3, 4)])
        self.assertEqual(list(database.get_generators_cache), [hashkey(database, 3)])

    async def test_deleting_child_invalidates_cached_parent_count(self):
        database = self.database
        parent = SimpleNamespace(guildId="1", generatorId="2")
        record = SimpleNamespace(VoiceGenerator=parent)
        database.db = Mock(
            generatedchannel=Mock(
                find_unique=AsyncMock(return_value=record), delete_many=AsyncMock()
            )
        )
        database.generator_cache[hashkey(database, 1, 2)] = record
        database.get_generators_cache[hashkey(database, 1)] = [record]
        database.generated_channel_cache[hashkey(database, "9")] = record
        await database.delete_generated_channel(9)
        self.assertFalse(database.generator_cache)
        self.assertFalse(database.get_generators_cache)
        self.assertFalse(database.generated_channel_cache)
        database.db.generatedchannel.delete_many.assert_awaited_once_with(
            where={"channelId": "9"}
        )

    async def test_deleting_already_missing_child_is_safe(self):
        database = self.database
        database.db = Mock(
            generatedchannel=Mock(
                find_unique=AsyncMock(return_value=None), delete_many=AsyncMock()
            )
        )
        database.generated_channel_cache[hashkey(database, 9)] = True
        await database.delete_generated_channel("9")
        self.assertFalse(database.generated_channel_cache)

    async def test_disconnect_without_connection_is_safe(self):
        database = self.database
        database.db = Mock(
            is_connected=Mock(return_value=False), disconnect=AsyncMock()
        )
        await database.disconnect()
        database.db.disconnect.assert_not_awaited()
