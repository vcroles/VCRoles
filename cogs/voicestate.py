import discord
from discord.ext import commands

from bot import MyClient
from voicestate.all import All
from voicestate.category import Category
from voicestate.generator import Generator
from voicestate.logging import Logging
from voicestate.permanent import Permanent
from voicestate.stage import Stage
from voicestate.voice import Voice


class VoiceState(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client
        self.all = All()
        self.category = Category()
        self.generator = Generator(client)
        self.logging = Logging(client)
        self.permanent = Permanent()
        self.stage = Stage()
        self.voice = Voice()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot == True:
            return

        # Joining
        if not before.channel and after.channel:
            roles_added = await self.join(member, before, after)

            if roles_added:
                (
                    voice_added,
                    stage_added,
                    category_added,
                    all_added,
                    perm_added,
                ) = roles_added

                await self.logging.log_join(
                    after,
                    member,
                    voice_added,
                    stage_added,
                    category_added,
                    all_added,
                    perm_added,
                )

        # Leaving
        elif before.channel and not after.channel:
            roles_removed = await self.leave(member, before, after)

            if roles_removed:
                (
                    voice_removed,
                    stage_removed,
                    category_removed,
                    all_removed,
                ) = roles_removed

                await self.logging.log_leave(
                    before,
                    member,
                    voice_removed,
                    stage_removed,
                    category_removed,
                    all_removed,
                )

        # Changing
        elif before.channel != after.channel:
            roles_removed = await self.leave(member, before, after)
            roles_added = await self.join(member, before, after)

            if roles_removed and roles_added:
                (
                    voice_removed,
                    stage_removed,
                    category_removed,
                    all_removed,
                ) = roles_removed

                (
                    voice_added,
                    stage_added,
                    category_added,
                    all_added,
                    perm_added,
                ) = roles_added

                await self.logging.log_change(
                    before,
                    after,
                    member,
                    voice_removed,
                    stage_removed,
                    category_removed,
                    voice_added,
                    stage_added,
                    category_added,
                )

    async def join(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        voice_added = stage_added = category_added = all_added = None

        try:
            after.channel.type
        except:
            return

        if isinstance(after.channel, discord.VoiceChannel):
            try:
                voice_added = await self.voice.join(
                    self.client.redis.get_linked("voice", member.guild.id),
                    member,
                    before,
                    after,
                )
            except:
                voice_added = None

        elif isinstance(after.channel, discord.StageChannel):
            try:
                stage_added = await self.stage.join(
                    self.client.redis.get_linked("stage", member.guild.id),
                    member,
                    before,
                    after,
                )
            except:
                stage_added = None

        try:
            category_added = await self.category.join(
                self.client.redis.get_linked("category", member.guild.id),
                member,
                before,
                after,
            )
        except:
            category_added = None

        try:
            all_added = await self.all.join(
                self.client.redis.get_linked("all", member.guild.id),
                member,
                before,
                after,
            )
        except:
            all_added = None

        try:
            perm_added = await self.permanent.join(
                self.client.redis.get_linked("permanent", member.guild.id),
                member,
                before,
                after,
            )
        except:
            perm_added = None

        try:
            await self.generator.join(member, before, after)
        except:
            pass

        return (voice_added, stage_added, category_added, all_added, perm_added)

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        voice_removed = stage_removed = category_removed = all_removed = None

        try:
            before.channel.type
        except:
            return

        try:
            all_removed = await self.all.leave(
                self.client.redis.get_linked("all", member.guild.id),
                member,
                before,
                after,
            )
        except:
            all_removed = None

        try:
            category_removed = await self.category.leave(
                self.client.redis.get_linked("category", member.guild.id),
                member,
                before,
                after,
            )
        except:
            category_removed = None

        if isinstance(before.channel, discord.StageChannel):
            try:
                stage_removed = await self.stage.leave(
                    self.client.redis.get_linked("stage", member.guild.id),
                    member,
                    before,
                    after,
                )
            except:
                stage_removed = None

        if isinstance(before.channel, discord.VoiceChannel):
            try:
                voice_removed = await self.voice.leave(
                    self.client.redis.get_linked("voice", member.guild.id),
                    member,
                    before,
                    after,
                )
            except:
                voice_removed = None

        try:
            await self.generator.leave(member, before, after)
        except:
            pass

        return (voice_removed, stage_removed, category_removed, all_removed)


def setup(client: MyClient):
    client.add_cog(VoiceState(client))
