import datetime

import discord
from prisma.enums import LinkType

from utils.client import VCRolesClient
from utils.types import LinkableChannel, VoiceStateReturnData


class Logging:
    def __init__(self, client: VCRolesClient):
        self.client = client

    @staticmethod
    def construct_embed(
        data: list[VoiceStateReturnData],
    ):

        added_chunks: list[str] = []
        removed_chunks: list[str] = []

        for item in data:
            if item.link_type in (LinkType.REGULAR, LinkType.STAGE):
                link_title = "Channel: "
            elif item.link_type == LinkType.CATEGORY:
                link_title = "Category: "
            elif item.link_type == LinkType.ALL:
                link_title = "All: "
            elif item.link_type == LinkType.PERMANENT:
                link_title = "Permanent: "
            else:
                continue

            if item.added:
                added_chunks.append(link_title)
                added_chunks.extend([role.mention + " " for role in item.added])
                added_chunks.append("\n")
            if item.removed:
                removed_chunks.append(link_title)
                removed_chunks.extend([role.mention + " " for role in item.removed])
                removed_chunks.append("\n")

        added_content = "".join(added_chunks).strip()
        removed_content = "".join(removed_chunks).strip()

        return added_content, removed_content

    async def log_join(
        self,
        user_channel: LinkableChannel,
        member: discord.Member,
        roles_changed: list[VoiceStateReturnData],
    ) -> None:
        guild_data = await self.client.db.get_guild_data(member.guild.id)

        if not guild_data.logging:
            return

        channel = member.guild.get_channel(int(guild_data.logging))

        if not channel or not isinstance(channel, discord.TextChannel):
            return

        logging_embed = discord.Embed(
            title=f"Member joined {'voice' if isinstance(user_channel, discord.VoiceChannel) else 'stage' if isinstance(user_channel, discord.StageChannel) else ''} channel",
            description=f"{member} joined {user_channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        logging_embed.set_footer(text=f"User ID - {member.id}")
        logging_embed.set_author(
            name=f"{member.name}#{member.discriminator}",
            icon_url=member.avatar.url if member.avatar else None,
        )

        added_content, removed_content = self.construct_embed(roles_changed)

        if added_content:
            logging_embed.add_field(
                name="Roles Added:", value=added_content, inline=False
            )
        if removed_content:
            logging_embed.add_field(
                name="Roles Removed:", value=removed_content, inline=False
            )

        try:
            await channel.send(embed=logging_embed)
        except:
            pass

    async def log_leave(
        self,
        user_channel: LinkableChannel,
        member: discord.Member,
        roles_changed: list[VoiceStateReturnData],
    ) -> None:
        guild_data = await self.client.db.get_guild_data(member.guild.id)

        if not guild_data.logging:
            return

        channel = self.client.get_channel(int(guild_data.logging))

        if not channel or not isinstance(channel, discord.TextChannel):
            return

        logging_embed = discord.Embed(
            title=f"Member left {'voice' if isinstance(user_channel, discord.VoiceChannel) else 'stage' if isinstance(user_channel, discord.StageChannel) else ''} channel",
            description=f"{member} left {user_channel.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        logging_embed.set_footer(text=f"User ID - {member.id}")
        logging_embed.set_author(
            name=f"{member.name}#{member.discriminator}",
            icon_url=member.avatar.url if member.avatar else None,
        )

        added_content, removed_content = self.construct_embed(roles_changed)

        if added_content:
            logging_embed.add_field(
                name="Roles Added:", value=added_content, inline=False
            )
        if removed_content:
            logging_embed.add_field(
                name="Roles Removed:", value=removed_content, inline=False
            )

        try:
            await channel.send(embed=logging_embed)
        except:
            pass

    async def log_change(
        self,
        user_before_channel: LinkableChannel,
        user_after_channel: LinkableChannel,
        member: discord.Member,
        leave_roles_changed: list[VoiceStateReturnData],
        join_roles_changed: list[VoiceStateReturnData],
    ):
        guild_data = await self.client.db.get_guild_data(member.guild.id)

        if not guild_data.logging:
            return

        channel = member.guild.get_channel(int(guild_data.logging))

        if not channel or not isinstance(channel, discord.TextChannel):
            return

        logging_embed = discord.Embed(
            title=f"Member moved channel",
            description=f"**Before:** {user_before_channel.mention}\n**+After:** {user_after_channel.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        logging_embed.set_footer(text=f"User ID - {member.id}")
        logging_embed.set_author(
            name=f"{member.name}#{member.discriminator}",
            icon_url=member.avatar.url if member.avatar else None,
        )

        added_content, removed_content = self.construct_embed(leave_roles_changed)

        if added_content:
            logging_embed.add_field(
                name="Roles Added From Leave:",
                value=added_content,
                inline=False,
            )
        if removed_content:
            logging_embed.add_field(
                name="Roles Removed From Leave:",
                value=removed_content,
                inline=False,
            )

        added_content, removed_content = self.construct_embed(join_roles_changed)

        if added_content:
            logging_embed.add_field(
                name="Roles Added From Join:", value=added_content, inline=False
            )
        if removed_content:
            logging_embed.add_field(
                name="Roles Removed From Join:",
                value=removed_content,
                inline=False,
            )

        try:
            await channel.send(embed=logging_embed)
        except:
            pass
