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
JoinableChannel = discord.StageChannel | discord.VoiceChannel


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


class SuffixConstructor:
    """Construct a suffix"""

    voice_suffix: str = ""
    stage_suffix: str = ""
    category_suffix: str = ""
    all_suffix: str = ""
    permanent_suffix: str = ""

    @property
    def suffix(self) -> str:
        """Get the suffixes as a single string (excludes permanent suffix)"""
        return " ".join(
            [
                self.voice_suffix or "",
                self.stage_suffix or "",
                self.category_suffix or "",
                self.all_suffix or "",
            ]
        ).strip()

    def add(self, link_type: LinkType, suffix: str) -> None:
        """Add a suffix to the constructor"""
        if link_type == LinkType.REGULAR:
            self.voice_suffix += suffix
        elif link_type == LinkType.STAGE:
            self.stage_suffix += suffix
        elif link_type == LinkType.CATEGORY:
            self.category_suffix += suffix
        elif link_type == LinkType.ALL:
            self.all_suffix += suffix
        elif link_type == LinkType.PERMANENT:
            self.permanent_suffix += suffix


class RoleCategory(enum.Enum):
    REGULAR = 1
    REVERSE = 2
    STAGE_SPEAKER = 3
