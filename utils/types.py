import enum
from typing import Literal, NamedTuple, Optional

import discord
from prisma.enums import LinkType
from prisma.models import Link

from config import ENVIRONMENT

if ENVIRONMENT == "DEV":
    using_topgg = False
else:
    using_topgg = True

DiscordID = str | int
LinkableChannel = discord.StageChannel | discord.VoiceChannel | discord.CategoryChannel


class LinkReturnData(NamedTuple):
    """Return data from linking"""

    status: bool
    message: str
    data: Optional[Link]


class MentionableRole:
    """A role which isn't cached but can still be mentioned"""

    def __init__(self, id: DiscordID) -> None:
        self.id = id

    @property
    def mention(self) -> str:
        return f"<@&{self.id}>"


RoleList = list[discord.Role | MentionableRole]


class VoiceStateReturnData(NamedTuple):
    """Return the roles added/removed"""

    join_leave: Literal["join", "leave"]
    link_type: LinkType
    added: RoleList = []
    removed: RoleList = []


class RoleCategory(enum.Enum):
    REGULAR = 1
    REVERSE = 2
    STAGE_SPEAKER = 3
