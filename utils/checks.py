"""
App command checks for the bot.
"""

from typing import Callable, TypeVar

from discord import Interaction, app_commands
from discord.app_commands.commands import Check

T = TypeVar("T")


def check_any(*checks) -> Callable[[T], T]:
    async def predicate(interaction: Interaction) -> bool:
        return any(check(interaction) for check in checks)

    return app_commands.check(predicate)


def is_owner(interaction: Interaction) -> bool:
    return interaction.user.id in [652797071623192576, 602235481459261440]


def command_available(interaction: Interaction) -> bool:
    client = interaction.client

    cmds_count = client.redis.get_user_cmd_count(interaction.user.id)

    if cmds_count >= 15:
        return False

    client.loop.create_task(
        client.ar.execute_command("hincrby", "commands", str(interaction.user.id), 1)
    )
    return True
