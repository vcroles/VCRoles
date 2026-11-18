"""Bounded, event-driven retries for permission failures, never a blacklist."""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from weakref import WeakValueDictionary

import discord
from aiohttp import ClientError
from cachetools import TTLCache

from utils.telemetry import get_telemetry
from utils.types import LogLevel


@dataclass
class RetryState:
    signature: object
    failures: int = 0
    retry_at: float = 0
    suppressed: int = 0
    probing: bool = False


class RetryOutcome(Enum):
    NOOP = "noop"
    DEFERRED = "deferred"


def guild_permissions_signature(guild):
    me = guild.me
    if me is None:
        return None
    return (me.guild_permissions.value, me.top_role.id, me.top_role.position)


def channel_permissions_signature(channel):
    me = channel.guild.me
    return (
        guild_permissions_signature(channel.guild),
        channel.is_obfuscated(),
        channel.permissions_for(me).value if me is not None else None,
    )


class PermissionBackoff:
    DELAYS = (30, 60, 120, 300, 600, 900)

    def __init__(self, client, *, clock=time.monotonic, maxsize=2**15):
        self.client = client
        self.clock = clock
        # Quiet resources eventually disappear; restarts also allow a fresh try.
        self.states = TTLCache(maxsize, 24 * 3600, timer=clock)
        # A successful HTTP trial takes precedence over an unchanged stale
        # negative cache entry. This cache is bounded and expires too.
        self.verified = TTLCache(maxsize, 24 * 3600, timer=clock)
        self.guild_probe_locks: WeakValueDictionary[tuple[int, str], asyncio.Lock] = (
            WeakValueDictionary()
        )

    def _log(self, event, operation, guild, resource_id, state, **context):
        self.client.log(
            LogLevel.INFO,
            "Permission retry state changed",
            event=event,
            operation=operation,
            guild_id=guild.id,
            shard_id=guild.shard_id,
            resource_id=resource_id,
            failures=state.failures,
            suppressed=state.suppressed,
            **context,
        )

    def clear(self, operation, guild, resource_id, *, reason="success"):
        key = (operation, guild.id, resource_id)
        self.verified.pop(key, None)
        state = self.states.pop(key, None)
        if state is not None:
            self._log(
                "permission_retry_recovered",
                operation,
                guild,
                resource_id,
                state,
                reason=reason,
            )
            get_telemetry().permission_retry(operation, "recovered")

    async def guild_permission(self, guild, permission: str) -> bool:
        key = (guild.id, permission)
        lock = self.guild_probe_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self.guild_probe_locks[key] = lock
        # Related events share a read-only probe. If it confirms recovery,
        # waiting events may proceed instead of losing their work to a race.
        async with lock:
            return await self._guild_permission(guild, permission)

    async def _guild_permission(self, guild, permission: str) -> bool:
        operation, reason = {
            "manage_roles": ("guild_roles", "manage_roles_missing"),
            "manage_nicknames": ("guild_nicknames", "manage_nicknames_missing"),
        }[permission]
        signature = guild_permissions_signature(guild)
        key = (operation, guild.id, guild.id)
        if guild.me is not None and getattr(guild.me.guild_permissions, permission):
            # Retire any old HTTP verification when the gateway cache catches
            # up, so a later permission revocation starts a fresh cooldown.
            self.clear(operation, guild, guild.id, reason="permissions_changed")
            return True
        if key in self.verified and self.verified[key] == signature:
            return True

        async def probe():
            # Read only the bot's own membership and current role definitions.
            # Member.roles/guild_permissions resolve through the gateway role
            # cache, so use the raw returned role IDs to avoid trusting stale
            # role definitions (including newly created roles absent there).
            member = await guild.fetch_member(self.client.user.id)
            roles = await guild.fetch_roles()
            role_ids = {guild.id, *member._roles}
            permissions = discord.Permissions.none()
            for role in roles:
                if role.id in role_ids:
                    permissions.value |= role.permissions.value
            if member.id == guild.owner_id or permissions.administrator:
                return
            if member.is_timed_out() or not getattr(permissions, permission):
                return RetryOutcome.DEFERRED

        try:
            return await self.run(
                operation,
                guild,
                guild.id,
                probe,
                signature=signature,
                unavailable=reason,
            )
        except (discord.HTTPException, ClientError, OSError) as error:
            # This path already has a negative permission cache. A failed
            # read-only check must not let every waiting event retry it in turn.
            get_telemetry().failure(error)
            self._failed(
                operation,
                guild,
                guild.id,
                signature,
                "permission_probe_unavailable",
                error,
            )
            return False

    def _recheck_guild_permission(self, operation, guild):
        capabilities = {
            "member_roles": ("guild_roles",),
            "member_nickname": ("guild_nicknames",),
            "member_fetch": ("guild_roles", "guild_nicknames"),
        }.get(operation, ())
        for capability in capabilities:
            key = (capability, guild.id, guild.id)
            if key not in self.verified:
                continue
            # A member-specific failure does not prove a guild permission was
            # revoked. Request a fresh self-check without imposing a cooldown.
            state = RetryState(self.verified.pop(key))
            self.states[key] = state
            self._log(
                "permission_retry_reset",
                capability,
                guild,
                guild.id,
                state,
                reason="member_forbidden",
            )
            get_telemetry().permission_retry(capability, "reset")

    def blocked(self, operation, guild, resource_id, *, signature=None):
        key = (operation, guild.id, resource_id)
        state = self.states.get(key)
        if key in self.verified and self.verified[key] != signature:
            self.verified.pop(key, None)
        if state is not None and state.signature != signature:
            self.states.pop(key, None)
            self._log(
                "permission_retry_reset",
                operation,
                guild,
                resource_id,
                state,
                reason="permissions_changed",
            )
            get_telemetry().permission_retry(operation, "reset")
            state = None
        if state is not None and (state.probing or self.clock() < state.retry_at):
            state.suppressed += 1
            get_telemetry().permission_retry(operation, "suppressed")
            get_telemetry().deferred()
            return True
        return False

    def _failed(
        self, operation, guild, resource_id, signature, reason, error=None, details=None
    ):
        key = (operation, guild.id, resource_id)
        self.verified.pop(key, None)
        state = self.states.get(key)
        if state is None:
            state = RetryState(signature)
        state.failures += 1
        delay = self.DELAYS[min(state.failures - 1, len(self.DELAYS) - 1)]
        state.retry_at = self.clock() + delay
        state.probing = False
        self.states[key] = state
        self._log(
            "permission_retry_scheduled",
            operation,
            guild,
            resource_id,
            state,
            reason=reason,
            retry_after_seconds=delay,
            discord_code=error.code
            if isinstance(error, discord.HTTPException)
            else None,
            error=error,
            **(details or {}),
        )
        state.suppressed = 0
        get_telemetry().permission_retry(operation, "failed")
        get_telemetry().deferred()

    def ready(
        self,
        operation,
        guild,
        resource_id,
        *,
        signature=None,
        unavailable=None,
        details=None,
    ):
        if self.blocked(operation, guild, resource_id, signature=signature):
            return False
        key = (operation, guild.id, resource_id)
        if unavailable and key not in self.states and key not in self.verified:
            # Avoid the first known-doomed request, but do not let a stale
            # negative permission cache suppress actual trials forever.
            self._failed(
                operation, guild, resource_id, signature, unavailable, details=details
            )
            return False
        return True

    async def run(
        self,
        operation,
        guild,
        resource_id,
        callback,
        *,
        signature=None,
        unavailable=None,
        details=None,
    ) -> bool:
        if not self.ready(
            operation,
            guild,
            resource_id,
            signature=signature,
            unavailable=unavailable,
            details=details,
        ):
            return False
        key = (operation, guild.id, resource_id)
        state = self.states.get(key)
        if state is not None:
            # Exactly one trial may run after a failed resource's cooldown.
            state.probing = True
        try:
            error = None
            if callback is not None:
                try:
                    outcome = await callback()
                    if outcome is RetryOutcome.NOOP:
                        # No request was needed or eligible. Leave an expired
                        # trial available to another candidate without claiming
                        # that the cached permissions were verified over HTTP.
                        return False
                    if outcome is RetryOutcome.DEFERRED:
                        # Extend only a separately established blocker. Member
                        # prerequisites have no guild-wide 'unavailable' reason;
                        # the read-only self-check determines shared recovery.
                        if (
                            unavailable
                            and state is not None
                            and self.states.get(key) is state
                        ):
                            self._failed(
                                operation,
                                guild,
                                resource_id,
                                signature,
                                unavailable,
                                details=details,
                            )
                        return False
                except discord.Forbidden as forbidden:
                    error = forbidden
                    unavailable = "discord_forbidden"
                    get_telemetry().failure(error)
                    self._recheck_guild_permission(operation, guild)
                else:
                    # A concurrent healthy request must not erase a newer failure.
                    if self.states.get(key) is state:
                        self.clear(operation, guild, resource_id)
                        if unavailable:
                            self.verified[key] = signature
                    return True
            self._failed(
                operation, guild, resource_id, signature, unavailable, error, details
            )
            return False
        finally:
            if state is not None:
                state.probing = False
