"""
App command checks for the bot.
"""

from typing import Awaitable, Callable, TypeVar

import redis
from discord import Interaction, app_commands

import config

from .client import VCRolesClient

T = TypeVar("T")


def check_any(*checks: Callable[[Interaction], Awaitable[bool]]) -> Callable[[T], T]:
    async def predicate(interaction: Interaction) -> bool:
        t: list[bool] = []
        t.extend([await check(interaction) for check in checks])
        return any(t)

    return app_commands.check(predicate)


async def is_owner(interaction: Interaction) -> bool:
    return interaction.user.id in [652797071623192576, 602235481459261440]


async def command_available(interaction: Interaction) -> bool:
    if config.ENVIRONMENT == "DEV":
        return True

    client = interaction.client
    if not isinstance(client, VCRolesClient):
        return True

    try:
        premium = await client.ar.hget("premium", str(interaction.user.id))
        if premium and str(premium) == "1":
            return True
    except redis.exceptions.RedisError:
        pass

    cmds_count = await client.ar.hget("commands", str(interaction.user.id))
    try:
        cmds_count = int(cmds_count) if cmds_count is not None else 0
    except ValueError:
        cmds_count = 0

    if cmds_count >= 15:
        return False

    client.loop.create_task(client.ar.hincrby("commands", str(interaction.user.id), 1))

    return True
