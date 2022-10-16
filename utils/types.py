import enum
import discord
from prisma.models import Link
from typing import NamedTuple, Optional

DiscordID = str | int
LinkableChannel = discord.StageChannel | discord.VoiceChannel | discord.CategoryChannel


class LinkReturnData(NamedTuple):
    """Return data from linking"""

    status: bool
    message: str
    data: Optional[Link]


class RoleCategory(enum.Enum):
    REGULAR = 1
    REVERSE = 2
    STAGE_SPEAKER = 3
