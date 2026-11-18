import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord

from utils.permission_backoff import PermissionBackoff, RetryOutcome


def forbidden():
    return discord.Forbidden(
        SimpleNamespace(status=403, reason="Forbidden"),
        {"code": 50013, "message": "Missing Permissions"},
    )


class PermissionBackoffTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = 1000.0
        self.client = Mock()
        self.guild = SimpleNamespace(id=1, shard_id=0)
        self.policy = PermissionBackoff(self.client, clock=lambda: self.now)
        self.callback = AsyncMock(side_effect=forbidden())

    async def run_attempt(self, **kwargs):
        return await self.policy.run(
            "member_roles", self.guild, 2, self.callback, **kwargs
        )

    async def test_progressive_backoff_caps_and_success_resets(self):
        for count, delay in enumerate((30, 60, 120, 300, 600, 900, 900), 1):
            self.assertFalse(await self.run_attempt())
            self.assertEqual(self.callback.await_count, count)
            self.now += delay - 0.01
            for _ in range(20):
                self.assertFalse(await self.run_attempt())
            self.assertEqual(self.callback.await_count, count)
            self.now += 0.01
        self.callback.side_effect = None
        self.assertTrue(await self.run_attempt())
        self.assertFalse(self.policy.states)
        recovered = self.client.log.call_args.kwargs
        self.assertEqual(recovered["event"], "permission_retry_recovered")
        self.assertEqual(recovered["suppressed"], 20)
        self.callback.side_effect = forbidden()
        await self.run_attempt()
        self.assertEqual(self.client.log.call_args.kwargs["retry_after_seconds"], 30)

    async def test_signature_change_allows_immediate_trial(self):
        await self.run_attempt(signature=1)
        self.callback.side_effect = None
        self.assertTrue(await self.run_attempt(signature=2))
        self.assertEqual(self.callback.await_count, 2)
        self.assertIn(
            "permission_retry_reset",
            [call.kwargs["event"] for call in self.client.log.call_args_list],
        )

    async def test_unobserved_permission_repair_recovers_at_next_due_event(self):
        await self.run_attempt()
        self.callback.side_effect = None
        self.assertFalse(await self.run_attempt())
        self.now += 30
        self.assertTrue(await self.run_attempt())

    async def test_cooldown_is_scoped_to_operation_guild_and_resource(self):
        await self.run_attempt()
        healthy = AsyncMock()
        for operation, guild, resource in (
            ("member_nickname", self.guild, 2),
            ("member_roles", SimpleNamespace(id=3, shard_id=0), 2),
            ("member_roles", self.guild, 4),
        ):
            self.assertTrue(await self.policy.run(operation, guild, resource, healthy))
        self.assertEqual(healthy.await_count, 3)

    async def test_only_one_due_trial_and_cancellation_releases_it(self):
        await self.run_attempt()
        self.now += 30
        started = asyncio.Event()
        hold = asyncio.Event()

        async def slow():
            started.set()
            await hold.wait()

        self.callback.side_effect = slow
        task = asyncio.create_task(self.run_attempt())
        await asyncio.wait_for(started.wait(), 1)
        for _ in range(20):
            self.assertFalse(await self.run_attempt())
        self.assertEqual(self.callback.await_count, 2)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.callback.side_effect = None
        self.assertTrue(await self.run_attempt())

    async def test_non_permission_errors_propagate_without_blacklisting(self):
        self.callback.side_effect = OSError("network error")
        with self.assertRaises(OSError):
            await self.run_attempt()
        self.assertFalse(self.policy.states)
        self.client.log.assert_not_called()

    async def test_known_missing_permissions_never_call_discord(self):
        for _ in range(20):
            self.assertFalse(await self.run_attempt(unavailable="manage_roles_missing"))
        self.callback.assert_not_awaited()
        self.client.log.assert_called_once()
        self.policy.clear("member_roles", self.guild, 2, reason="permissions_changed")
        self.callback.side_effect = None
        self.assertTrue(await self.run_attempt())

    async def test_stale_negative_cache_allows_due_http_trial_then_stays_healthy(self):
        self.callback.side_effect = None
        self.assertFalse(await self.run_attempt(unavailable="manage_roles_missing"))
        self.callback.assert_not_awaited()
        self.now += 30
        self.assertTrue(await self.run_attempt(unavailable="manage_roles_missing"))
        # A successful request overrides the unchanged negative snapshot.
        self.assertTrue(await self.run_attempt(unavailable="manage_roles_missing"))
        self.assertEqual(self.callback.await_count, 2)
        self.assertFalse(self.policy.states)

    async def test_due_http_failure_advances_known_permission_cooldown(self):
        await self.run_attempt(unavailable="manage_roles_missing")
        self.now += 30
        self.assertFalse(await self.run_attempt(unavailable="manage_roles_missing"))
        self.callback.assert_awaited_once()
        self.assertEqual(self.client.log.call_args.kwargs["retry_after_seconds"], 60)

    async def test_noop_leaves_due_trial_available_without_verifying_permissions(self):
        await self.run_attempt(unavailable="manage_roles_missing")
        self.now += 30
        self.callback.side_effect = None
        self.callback.return_value = RetryOutcome.NOOP
        self.assertFalse(await self.run_attempt(unavailable="manage_roles_missing"))
        state = self.policy.states[("member_roles", 1, 2)]
        self.assertEqual((state.failures, state.retry_at), (1, self.now))
        self.assertFalse(state.probing)
        self.assertFalse(self.policy.verified)
        self.client.log.assert_called_once()
        self.callback.return_value = None
        self.assertTrue(await self.run_attempt(unavailable="manage_roles_missing"))

    async def test_deferred_prerequisite_advances_known_guild_cooldown(self):
        await self.run_attempt(unavailable="manage_roles_missing")
        self.now += 30
        self.callback.side_effect = None
        self.callback.return_value = RetryOutcome.DEFERRED
        self.assertFalse(await self.run_attempt(unavailable="manage_roles_missing"))
        state = self.policy.states[("member_roles", 1, 2)]
        self.assertEqual((state.failures, state.retry_at), (2, self.now + 60))
        self.assertFalse(state.probing)
        self.assertFalse(await self.run_attempt(unavailable="manage_roles_missing"))
        self.callback.assert_awaited_once()

    async def test_cache_is_bounded_and_quiet_resources_expire(self):
        self.policy = PermissionBackoff(self.client, clock=lambda: self.now, maxsize=2)
        for resource in (1, 2, 3):
            await self.policy.run("member_roles", self.guild, resource, self.callback)
        self.assertEqual(len(self.policy.states), 2)
        self.now += 24 * 3600
        self.assertFalse(self.policy.states)

    async def test_older_success_does_not_erase_concurrent_failure(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def old_success():
            entered.set()
            await release.wait()

        task = asyncio.create_task(
            self.policy.run("member_roles", self.guild, 2, old_success)
        )
        await asyncio.wait_for(entered.wait(), 1)
        await self.run_attempt()
        release.set()
        self.assertTrue(await task)
        self.assertTrue(self.policy.blocked("member_roles", self.guild, 2))


class GuildPermissionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = 1000.0
        self.client = Mock(user=SimpleNamespace(id=666))
        self.guild = Mock(id=1, shard_id=0, owner_id=999)
        self.guild.me = SimpleNamespace(
            guild_permissions=discord.Permissions.none(),
            top_role=SimpleNamespace(id=7, position=1),
        )
        self.member = SimpleNamespace(id=666, _roles=[7], is_timed_out=lambda: False)
        self.role = SimpleNamespace(
            id=7,
            permissions=discord.Permissions(manage_roles=True, manage_nicknames=True),
        )
        self.guild.fetch_member = AsyncMock(return_value=self.member)
        self.guild.fetch_roles = AsyncMock(return_value=[self.role])
        self.policy = PermissionBackoff(self.client, clock=lambda: self.now)

    async def test_healthy_cached_permissions_do_not_add_requests(self):
        self.guild.me.guild_permissions = self.role.permissions
        for _ in range(10):
            self.assertTrue(
                await self.policy.guild_permission(self.guild, "manage_roles")
            )
            self.assertTrue(
                await self.policy.guild_permission(self.guild, "manage_nicknames")
            )
        self.guild.fetch_member.assert_not_awaited()
        self.guild.fetch_roles.assert_not_awaited()

    async def test_only_self_permissions_determine_shared_cooldown_and_recovery(self):
        self.role.permissions.manage_roles = False
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.guild.fetch_member.assert_awaited_once_with(666)
        self.guild.fetch_roles.assert_awaited_once()
        state = self.policy.states[("guild_roles", 1, 1)]
        self.assertEqual(state.retry_at, self.now + 60)
        self.role.permissions.manage_roles = True
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 60
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertFalse(self.policy.states)
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertEqual(self.guild.fetch_roles.await_count, 2)

    async def test_bot_membership_and_role_definitions_are_both_authoritative(self):
        # The public Member.guild_permissions property still uses cached roles.
        # A real returned Member with a new role must be checked against the
        # fresh role definitions, even while those cached definitions deny it.
        cached = discord.Role(
            guild=self.guild,
            state=Mock(),
            data={
                "id": "7",
                "name": "Bot",
                "position": 1,
                "permissions": "0",
            },
        )
        everyone = discord.Role(
            guild=self.guild,
            state=Mock(),
            data={
                "id": "1",
                "name": "@everyone",
                "position": 0,
                "permissions": "0",
            },
        )
        self.guild.default_role = everyone
        self.guild.get_role.side_effect = {1: everyone, 7: cached}.get
        state = Mock()
        state.store_user.side_effect = lambda data: discord.User(state=state, data=data)
        member = discord.Member(
            guild=self.guild,
            state=state,
            data={
                "user": {
                    "id": "666",
                    "username": "Bot",
                    "discriminator": "0",
                    "avatar": None,
                },
                "roles": ["7"],
                "joined_at": None,
                "flags": 0,
            },
        )
        self.assertFalse(member.guild_permissions.manage_roles)
        self.guild.fetch_member.return_value = member
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertFalse(member.guild_permissions.manage_roles)
        self.assertEqual(cached.permissions.value, 0)

    async def test_everyone_and_administrator_grants_are_respected(self):
        for grant in ("everyone", "administrator"):
            with self.subTest(grant=grant):
                policy = PermissionBackoff(self.client, clock=lambda: self.now)
                self.role.permissions = discord.Permissions(
                    administrator=grant == "administrator"
                )
                self.guild.fetch_roles.return_value = [self.role]
                if grant == "everyone":
                    self.guild.fetch_roles.return_value.append(
                        SimpleNamespace(
                            id=1, permissions=discord.Permissions(manage_roles=True)
                        )
                    )
                self.assertFalse(
                    await policy.guild_permission(self.guild, "manage_roles")
                )
                self.now += 30
                self.assertTrue(
                    await policy.guild_permission(self.guild, "manage_roles")
                )

    async def test_permissions_of_unassigned_roles_are_not_granted(self):
        self.role.permissions = discord.Permissions.none()
        self.guild.fetch_roles.return_value.append(
            SimpleNamespace(id=99, permissions=discord.Permissions(administrator=True))
        )
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertFalse(self.policy.verified)

    async def test_role_and_nickname_permissions_recover_independently(self):
        self.role.permissions.manage_roles = False
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertFalse(
            await self.policy.guild_permission(self.guild, "manage_nicknames")
        )
        self.now += 30
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertTrue(
            await self.policy.guild_permission(self.guild, "manage_nicknames")
        )
        self.assertIn(("guild_roles", 1, 1), self.policy.states)
        self.assertNotIn(("guild_nicknames", 1, 1), self.policy.states)

    async def test_later_revocation_of_http_verified_permission_gets_a_self_recheck(
        self,
    ):
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.role.permissions.manage_roles = False
        callback = AsyncMock(side_effect=forbidden())
        self.assertFalse(await self.policy.run("member_roles", self.guild, 2, callback))
        # No time passes: only a self-check, not that member's 403, may decide
        # whether the guild-wide cooldown should start again.
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertEqual(self.guild.fetch_roles.await_count, 2)
        self.assertEqual(self.policy.states[("guild_roles", 1, 1)].failures, 1)

    async def test_gateway_catchup_retires_old_verification_before_new_revocation(self):
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.guild.me.guild_permissions.manage_roles = True
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertFalse(self.policy.verified)
        self.guild.me.guild_permissions.manage_roles = False
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.assertIn(("guild_roles", 1, 1), self.policy.states)

    async def test_probe_transport_failures_back_off_without_repeated_requests(self):
        for error in (
            OSError("connection lost"),
            discord.HTTPException(
                SimpleNamespace(status=503, reason="Unavailable"), "unavailable"
            ),
        ):
            with self.subTest(error=type(error).__name__):
                policy = PermissionBackoff(self.client, clock=lambda: self.now)
                self.guild.fetch_member.reset_mock(side_effect=True)
                self.assertFalse(
                    await policy.guild_permission(self.guild, "manage_roles")
                )
                self.now += 30
                self.guild.fetch_member.side_effect = error
                for _ in range(10):
                    self.assertFalse(
                        await policy.guild_permission(self.guild, "manage_roles")
                    )
                self.guild.fetch_member.assert_awaited_once_with(666)
                state = policy.states[("guild_roles", 1, 1)]
                self.assertEqual(state.retry_at, self.now + 60)
                self.assertEqual(
                    self.client.log.call_args.kwargs["reason"],
                    "permission_probe_unavailable",
                )
                self.guild.fetch_member.side_effect = None
                self.now += 60
                self.assertTrue(
                    await policy.guild_permission(self.guild, "manage_roles")
                )

    async def test_cancelled_self_probe_releases_waiting_permission_check(self):
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        started, release = asyncio.Event(), asyncio.Event()

        async def fetch(member_id):
            started.set()
            await release.wait()
            return self.member

        self.guild.fetch_member.side_effect = fetch
        first = asyncio.create_task(
            self.policy.guild_permission(self.guild, "manage_roles")
        )
        await asyncio.wait_for(started.wait(), 1)
        second = asyncio.create_task(
            self.policy.guild_permission(self.guild, "manage_roles")
        )
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        release.set()
        self.assertTrue(await asyncio.wait_for(second, 1))
        self.guild.fetch_roles.assert_awaited_once()
        self.assertFalse(self.policy.states)

    async def test_permission_calculation_preserves_timeout_and_admin_rules(self):
        self.member.is_timed_out = lambda: True
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.now += 30
        self.assertFalse(await self.policy.guild_permission(self.guild, "manage_roles"))
        self.role.permissions.administrator = True
        self.now += 60
        self.assertTrue(await self.policy.guild_permission(self.guild, "manage_roles"))
