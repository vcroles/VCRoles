import asyncio
import uuid
from string import Template
from time import monotonic
from weakref import WeakValueDictionary

import discord
from cachetools import TTLCache
from prisma.enums import VoiceGeneratorOption, VoiceGeneratorType

from utils.client import VCRolesClient
from utils.logging import audit_event
from utils.types import JoinableChannel, LogLevel


class Generator:
    CLEANUP_GRACE_SECONDS = 60

    def __init__(self, client: VCRolesClient):
        self.client = client
        self.locks: WeakValueDictionary[tuple[int, int], asyncio.Lock] = (
            WeakValueDictionary()
        )
        self.recent_channels: TTLCache[int, bool] = TTLCache(2**15, 60)
        self.empty_channels: TTLCache[int, tuple[float, float]] = TTLCache(
            2**15, 15 * 60
        )
        self.shard_ready_after: dict[int, float] = {}

    def shard_disconnected(self, shard_id: int) -> None:
        self.shard_ready_after[shard_id] = float("inf")

    def shard_available(self, shard_id: int) -> None:
        self.shard_ready_after[shard_id] = monotonic() + self.CLEANUP_GRACE_SECONDS

    def can_cleanup(self, guild: discord.Guild) -> bool:
        shard = self.client.get_shard(guild.shard_id)
        return (
            self.client.is_ready()
            and not guild.unavailable
            and shard is not None
            and not shard.is_closed()
            and monotonic() >= self.shard_ready_after.get(guild.shard_id, 0)
        )

    def lock(self, guild_id: int, generator_id: int) -> asyncio.Lock:
        key = (guild_id, generator_id)
        lock = self.locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self.locks[key] = lock
        return lock

    async def join(
        self,
        member: discord.Member,
        user_channel: JoinableChannel,
    ) -> None:
        if isinstance(user_channel, discord.StageChannel):
            return

        if not user_channel:
            return

        channel_data = await self.client.db.get_generated_channel(user_channel.id)
        generator_id = (
            int(channel_data.VoiceGenerator.generatorId)
            if channel_data and channel_data.VoiceGenerator
            else user_channel.id
        )
        async with self.lock(member.guild.id, generator_id):
            # VoiceState is read from the guild's current gateway state, even
            # when this Member was copied before waiting for the lock.
            if not member.voice or member.voice.channel != user_channel:
                return
            if channel_data and channel_data.textChannelId:
                text_channel = await self.text_channel(member.guild, channel_data)
                if not member.voice or member.voice.channel != user_channel:
                    return
                if text_channel is not None:
                    overwrite = text_channel.overwrites_for(member)
                    overwrite.view_channel = True
                    overwrite.send_messages = True
                    await text_channel.set_permissions(member, overwrite=overwrite)
            await self._create(member, user_channel)

    async def text_channel(self, guild, data):
        if not data.textChannelId:
            return None
        channel = guild.get_channel(int(data.textChannelId))
        if channel is None:
            try:
                channel = await guild.fetch_channel(int(data.textChannelId))
            except discord.NotFound:
                return None
        if not isinstance(channel, discord.TextChannel):
            raise ValueError(
                f"Generated text channel {data.textChannelId} has wrong type"
            )
        return channel

    async def _create(self, member: discord.Member, user_channel: discord.VoiceChannel):
        gen_data = await self.client.db.get_generator(member.guild.id, user_channel.id)

        if not gen_data:
            return

        if gen_data.restrictRole:
            restricted_role = member.get_role(int(gen_data.restrictRole))
            if restricted_role:
                try:
                    await member.move_to(None)
                except discord.HTTPException:
                    pass
                return

        count = len(gen_data.openChannels) if gen_data.openChannels else 0
        editable = VoiceGeneratorOption.EDITABLE in gen_data.defaultOptions
        restricted_role = (
            member.guild.get_role(int(gen_data.restrictRole))
            if gen_data.restrictRole
            else None
        )

        if str(user_channel.id) != gen_data.generatorId:
            return

        if count >= gen_data.channelLimit:
            try:
                await member.move_to(None)
            except discord.HTTPException:
                pass
            return

        if gen_data.defaultRole:
            default_role = member.guild.get_role(int(gen_data.defaultRole))
            if not default_role:
                default_role = member.guild.default_role
        else:
            default_role = member.guild.default_role

        overwrites: dict[
            discord.Role | discord.Member, discord.PermissionOverwrite
        ] = {}

        if VoiceGeneratorOption.LOCK in gen_data.defaultOptions:
            try:
                overwrites[default_role].connect = False
            except KeyError:
                overwrites[default_role] = discord.PermissionOverwrite(connect=False)
        if VoiceGeneratorOption.HIDE in gen_data.defaultOptions:
            try:
                overwrites[default_role].view_channel = False
            except KeyError:
                overwrites[default_role] = discord.PermissionOverwrite(
                    view_channel=False
                )
        if restricted_role:
            try:
                overwrites[restricted_role].connect = False
            except KeyError:
                overwrites[restricted_role] = discord.PermissionOverwrite(connect=False)

        channel = None
        text_channel = None
        move_started = False
        operation_id = uuid.uuid4().hex
        phase = "voice_create"
        context = {
            "operation_id": operation_id,
            "guild_id": member.guild.id,
            "shard_id": member.guild.shard_id,
            "member_id": member.id,
            "generator_id": user_channel.id,
        }

        async def create_resources():
            nonlocal channel, text_channel, phase
            audit_event("generator_create_requested", kind="voice", **context)
            if gen_data.type == VoiceGeneratorType.CLONED:
                channel = await user_channel.clone(
                    name=f"[{user_channel.name}] #{count + 1}",
                    reason=f"Voice Channel Generator operation={operation_id}",
                )
            elif gen_data.type == VoiceGeneratorType.NUMBERED:
                channel = await member.guild.create_voice_channel(
                    name=f"{gen_data.channelName} #{count + 1}",
                    category=user_channel.category,
                    reason=f"Voice Channel Generator operation={operation_id}",
                    overwrites={
                        member.guild.me: discord.PermissionOverwrite(
                            manage_channels=True, connect=True, view_channel=True
                        ),
                        **overwrites,
                    },
                    user_limit=gen_data.defaultUserLimit,
                )
            elif gen_data.type == VoiceGeneratorType.CUSTOM_NAME:
                channel = await member.guild.create_voice_channel(
                    name=Template(
                        gen_data.channelName if gen_data.channelName else "$username"
                    ).substitute(username=member.display_name, count=count + 1),
                    category=user_channel.category,
                    reason=f"Voice Channel Generator operation={operation_id}",
                    overwrites={
                        member.guild.me: discord.PermissionOverwrite(
                            manage_channels=True, connect=True, view_channel=True
                        ),
                        **overwrites,
                    },
                    user_limit=gen_data.defaultUserLimit,
                )
            else:
                channel = await member.guild.create_voice_channel(
                    name=f"{member.display_name}",
                    category=user_channel.category,
                    reason=f"Voice Channel Generator operation={operation_id}",
                    overwrites={
                        member.guild.me: discord.PermissionOverwrite(
                            manage_channels=True, connect=True, view_channel=True
                        ),
                        **overwrites,
                    },
                    user_limit=gen_data.defaultUserLimit,
                )

            # Give the gateway time to report the initial member move before
            # reconciliation decides that this channel is abandoned.
            audit_event(
                "generator_channel_created",
                kind="voice",
                channel_id=channel.id,
                **context,
            )
            self.recent_channels[channel.id] = True
            phase = "voice_record"
            await self.client.db.create_generated_channel(
                member.guild.id, user_channel.id, channel.id, member.id, editable
            )

            if VoiceGeneratorOption.TEXT in gen_data.defaultOptions:
                phase = "text_create"
                audit_event(
                    "generator_create_requested",
                    kind="text",
                    voice_channel_id=channel.id,
                    **context,
                )
                text_channel = await member.guild.create_text_channel(
                    name=f"{member.display_name}-text",
                    category=user_channel.category,
                    reason=f"Voice Channel Generator operation={operation_id}",
                    overwrites={
                        member.guild.me: discord.PermissionOverwrite(
                            manage_channels=True, send_messages=True, view_channel=True
                        ),
                        member: discord.PermissionOverwrite(
                            view_channel=True, send_messages=True
                        ),
                        default_role: discord.PermissionOverwrite(
                            view_channel=False, send_messages=False
                        ),
                    },
                )
                audit_event(
                    "generator_channel_created",
                    kind="text",
                    channel_id=text_channel.id,
                    voice_channel_id=channel.id,
                    **context,
                )
                phase = "text_record"
                await self.client.db.update_generated_channel(
                    channel.id, text_channel_id=str(text_channel.id)
                )
            else:
                text_channel = None

        try:
            creation = asyncio.create_task(create_resources())
            try:
                await asyncio.shield(creation)
            except asyncio.CancelledError:
                # Ordinary cancellation must not abandon a successful create
                # before its ID and database record are available for rollback.
                try:
                    await creation
                finally:
                    raise
            audit_event(
                "generator_resources_persisted",
                voice_channel_id=channel.id,
                text_channel_id=text_channel.id if text_channel is not None else None,
                **context,
            )
            if text_channel is not None:
                phase = "text_notification"
                await text_channel.send(
                    f"{member.mention} this is your generated text channel."
                )
            if not member.voice or member.voice.channel != user_channel:
                await self._cleanup(
                    channel, text_channel, reason="member_left_before_move"
                )
                return
            move_started = True
            phase = "member_move"
            await member.move_to(channel)

        except (Exception, asyncio.CancelledError) as error:
            self.client.log(
                LogLevel.INFO
                if isinstance(error, asyncio.CancelledError)
                else LogLevel.ERROR,
                "Generator creation interrupted",
                error=None if isinstance(error, asyncio.CancelledError) else error,
                event="generator_creation_interrupted",
                phase=phase,
                cleanup_deferred=move_started,
                voice_channel_id=channel.id if channel is not None else None,
                text_channel_id=text_channel.id if text_channel is not None else None,
                **context,
            )
            if move_started:
                audit_event(
                    "generator_cleanup_deferred",
                    reason="move_outcome_uncertain",
                    voice_channel_id=channel.id,
                    **context,
                )
                # The move may have succeeded before its response/event arrived.
                # Preserve the persisted resources for healthy, repeated empty
                # observations rather than trusting the immediately stale cache.
                self.recent_channels[channel.id] = True
                self.empty_channels.pop(channel.id, None)
            else:
                await self._cleanup(channel, text_channel, reason="creation_rollback")
            raise

        if gen_data.hideAtLimit and count + 1 >= gen_data.channelLimit:
            gen_channel = member.guild.get_channel(int(gen_data.generatorId))
            if gen_channel:
                gen_overwrites = gen_channel.overwrites
                try:
                    gen_overwrites[default_role].view_channel = False
                except KeyError:
                    gen_overwrites[default_role] = discord.PermissionOverwrite(
                        view_channel=False
                    )
                try:
                    await gen_channel.edit(overwrites=gen_overwrites)
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

        self.client.log(
            LogLevel.DEBUG,
            f"Generated c/{channel.id} m/{member.id} g/{member.guild.id}",
        )

    async def leave(
        self,
        member: discord.Member,
        user_channel: JoinableChannel,
    ):
        if not user_channel:
            return

        data = await self.client.db.get_generated_channel(user_channel.id)
        if not data or not data.VoiceGenerator:
            return

        async with self.lock(member.guild.id, int(data.VoiceGenerator.generatorId)):
            # Reuse gateway state; ordinary channels require no REST request.
            voice_channel = self.client.get_channel(user_channel.id)
            if not isinstance(voice_channel, discord.VoiceChannel):
                return
            await self._leave(member, voice_channel, data)

    async def _leave(self, member, voice_channel, data):
        if member.voice and member.voice.channel == voice_channel:
            # A delayed leave event must not revoke access after a rejoin.
            return
        if not voice_channel.voice_states:
            text_channel = await self.text_channel(voice_channel.guild, data)
            if not await self._cleanup(
                voice_channel, text_channel, reason="member_leave"
            ):
                return

            if data.VoiceGenerator and data.VoiceGenerator.hideAtLimit:
                if data.VoiceGenerator.defaultRole:
                    default_role = member.guild.get_role(
                        int(data.VoiceGenerator.defaultRole)
                    )
                    if not default_role:
                        default_role = member.guild.default_role
                else:
                    default_role = member.guild.default_role

                count = await self.client.db.db.generatedchannel.count(
                    where={"voiceGeneratorId": data.voiceGeneratorId}
                )
                if count < data.VoiceGenerator.channelLimit:
                    gen_channel = member.guild.get_channel(
                        int(data.VoiceGenerator.generatorId)
                    )
                    if gen_channel:
                        overwrites = gen_channel.overwrites

                        try:
                            overwrites[default_role].view_channel = True
                        except KeyError:
                            overwrites[default_role] = discord.PermissionOverwrite(
                                view_channel=True
                            )

                        await gen_channel.edit(overwrites=overwrites)
        else:
            text_channel = await self.text_channel(member.guild, data)
            if member.voice and member.voice.channel == voice_channel:
                return
            if text_channel is not None:
                overwrite = text_channel.overwrites_for(member)
                overwrite.send_messages = False
                overwrite.view_channel = False
                await text_channel.set_permissions(member, overwrite=overwrite)

        self.client.log(
            LogLevel.DEBUG,
            f"Generator left c/{voice_channel.id} m/{member.id} g/{member.guild.id}",
        )

    async def _delete_record(self, channel_id, guild, *, reason, operation_id):
        context = {
            "operation_id": operation_id,
            "guild_id": guild.id,
            "shard_id": guild.shard_id,
            "voice_channel_id": channel_id,
            "reason": reason,
        }
        audit_event("generator_record_delete_requested", **context)
        try:
            await self.client.db.delete_generated_channel(channel_id)
        except Exception as error:
            audit_event("generator_record_delete_failed", error=error, **context)
            raise
        audit_event("generator_record_deleted", **context)
        self.empty_channels.pop(int(channel_id), None)

    async def _cleanup(
        self,
        voice_channel,
        text_channel,
        *,
        reason="generated_cleanup",
        observed_empty_seconds=None,
        operation_id=None,
    ) -> bool:
        """Persist intents before deletes; keep records when any deletion fails."""
        guild = (
            voice_channel.guild
            if voice_channel is not None
            else text_channel.guild
            if text_channel is not None
            else None
        )
        operation_id = operation_id or uuid.uuid4().hex
        context = {
            "operation_id": operation_id,
            "guild_id": guild.id if guild else None,
            "shard_id": guild.shard_id if guild else None,
            "reason": reason,
            "voice_channel_id": voice_channel.id if voice_channel is not None else None,
            "text_channel_id": text_channel.id if text_channel is not None else None,
            "observed_empty_seconds": observed_empty_seconds,
        }
        success = True
        for channel in (text_channel, voice_channel):
            if channel is None:
                continue
            if (guild is not None and not self.can_cleanup(guild)) or (
                voice_channel is not None and voice_channel.voice_states
            ):
                self.client.log(
                    LogLevel.DEBUG,
                    "Generated channel cleanup deferred",
                    event="generator_cleanup_guarded",
                    **context,
                )
                return False
            # This synchronous audit write/fsync must succeed before Discord is
            # called. An absent outcome after an intent means the result is unknown.
            audit_event(
                "generator_channel_delete_requested",
                channel_id=channel.id,
                occupants=len(voice_channel.voice_states)
                if voice_channel is not None
                else None,
                **context,
            )
            outcome = "deleted"
            try:
                await channel.delete(
                    reason=f"Generated channel cleanup operation={operation_id}"
                )
            except discord.NotFound:
                outcome = "already_missing"
            except discord.HTTPException as error:
                success = False
                audit_event(
                    "generator_channel_delete_failed",
                    error=error,
                    channel_id=channel.id,
                    **context,
                )
                continue
            audit_event(
                "generator_channel_delete_completed",
                channel_id=channel.id,
                outcome=outcome,
                **context,
            )
        if guild is not None and not self.can_cleanup(guild):
            return False
        if success and voice_channel is not None:
            await self._delete_record(
                voice_channel.id, guild, reason=reason, operation_id=operation_id
            )
        return success

    async def reconcile(self):
        """Recover recorded empty/missing channels after restarts or failed cleanup."""
        if not self.client.is_ready():
            return
        records = await self.client.db.db.generatedchannel.find_many(
            include={"VoiceGenerator": True}
        )
        stats = {
            "scanned": len(records),
            "cleaned": 0,
            "failed": 0,
            "unavailable": 0,
            "grace": 0,
            "occupied_or_wrong_type": 0,
        }
        try:
            for data in records:
                if not self.client.is_ready():
                    return
                generator = data.VoiceGenerator
                if not generator:
                    continue
                guild = self.client.get_guild(int(generator.guildId))
                if guild is None or not self.can_cleanup(guild):
                    stats["unavailable"] += 1
                    continue
                async with self.lock(guild.id, int(generator.generatorId)):
                    try:
                        if not self.can_cleanup(guild):
                            continue
                        if int(data.channelId) in self.recent_channels:
                            stats["grace"] += 1
                            continue
                        channel = guild.get_channel(int(data.channelId))
                        if channel is not None and (
                            not isinstance(channel, discord.VoiceChannel)
                            or channel.voice_states
                        ):
                            stats["occupied_or_wrong_type"] += 1
                            self.empty_channels.pop(int(data.channelId), None)
                            continue
                        # Cache misses are not proof of deletion. Confirm missing
                        # channels through REST before removing their database row.
                        if channel is None:
                            try:
                                channel = await guild.fetch_channel(int(data.channelId))
                            except discord.NotFound:
                                channel = None
                            if channel is not None:
                                # REST channel objects have no trustworthy voice
                                # membership when absent from the gateway cache.
                                self.empty_channels.pop(int(data.channelId), None)
                                continue
                        epoch = self.shard_ready_after.get(guild.shard_id, 0)
                        observed_epoch, first_empty = self.empty_channels.get(
                            int(data.channelId), (epoch, monotonic())
                        )
                        if observed_epoch != epoch:
                            first_empty = monotonic()
                        self.empty_channels[int(data.channelId)] = (epoch, first_empty)
                        if monotonic() - first_empty < self.CLEANUP_GRACE_SECONDS:
                            stats["grace"] += 1
                            continue
                        if not self.can_cleanup(guild):
                            continue
                        text_channel = await self.text_channel(guild, data)
                        if not self.can_cleanup(guild):
                            continue
                        operation_id = uuid.uuid4().hex
                        reason = (
                            "reconcile_missing"
                            if channel is None
                            else "reconcile_empty"
                        )
                        if await self._cleanup(
                            channel,
                            text_channel,
                            reason=reason,
                            operation_id=operation_id,
                            observed_empty_seconds=round(monotonic() - first_empty, 3),
                        ):
                            if channel is None:
                                await self._delete_record(
                                    data.channelId,
                                    guild,
                                    reason=reason,
                                    operation_id=operation_id,
                                )
                            stats["cleaned"] += 1
                            self.empty_channels.pop(int(data.channelId), None)
                            if generator.hideAtLimit:
                                count = await self.client.db.db.generatedchannel.count(
                                    where={"voiceGeneratorId": data.voiceGeneratorId}
                                )
                                trigger = guild.get_channel(int(generator.generatorId))
                                if trigger and count < generator.channelLimit:
                                    role = (
                                        guild.get_role(int(generator.defaultRole))
                                        if generator.defaultRole
                                        else None
                                    )
                                    role = role or guild.default_role
                                    overwrite = trigger.overwrites_for(role)
                                    overwrite.view_channel = True
                                    await trigger.set_permissions(
                                        role, overwrite=overwrite
                                    )
                    except Exception as error:
                        stats["failed"] += 1
                        self.client.log(
                            LogLevel.ERROR,
                            "Generated channel reconciliation failed",
                            error=error,
                            event="generator_reconcile_failed",
                            guild_id=guild.id,
                            shard_id=guild.shard_id,
                            generator_id=generator.generatorId,
                            voice_channel_id=data.channelId,
                            text_channel_id=data.textChannelId,
                        )
        finally:
            self.client.log(
                LogLevel.INFO,
                "Generator reconciliation completed",
                event="generator_reconcile_summary",
                **stats,
            )
