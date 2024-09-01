import asyncio
import datetime

import discord

from prisma.enums import LinkType
from utils.client import VCRolesClient
from utils.types import LinkableChannel, LogLevel, VoiceStateReturnData


class Logging:
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.embed_queues: dict[int, asyncio.Queue] = {}
        self.client.loop.create_task(self.process_queues())
        self.continue_processing = True

    async def process_queues(self):
        while self.continue_processing:
            try:
                await self._process_queues()

                # Wait for 5 seconds before the next processing cycle to reduce the number of messages sent
                # Technically this is 5 seconds + the time it takes to process the queues, but the extra is unimportant
                await asyncio.sleep(5)
            except Exception as e:
                self.client.log(LogLevel.ERROR, f"Error processing embed queues: {e}")

    async def _process_queues(self):
        embed_queues = self.embed_queues.copy()
        self.embed_queues.clear()

        for guild_id, queue in embed_queues.items():
            if queue.empty():
                continue

            guild_data = await self.client.db.get_guild_data(guild_id)
            if not guild_data.logging:
                continue

            channel = self.client.get_channel(int(guild_data.logging))
            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            while not queue.empty():
                embeds = []
                while not queue.empty() and len(embeds) < 10:
                    embeds.append(await queue.get())

                if embeds:
                    try:
                        await channel.send(embeds=embeds)
                    except discord.Forbidden:
                        pass
                    except discord.HTTPException:
                        pass

    async def stop(self):
        self.continue_processing = False

        # Process any remaining embeds in the queue
        await self._process_queues()

    async def add_to_queue(self, guild_id: int, embed: discord.Embed):
        if guild_id not in self.embed_queues:
            self.embed_queues[guild_id] = asyncio.Queue()
        await self.embed_queues[guild_id].put(embed)

    @staticmethod
    def construct_embed(
        data: list[VoiceStateReturnData],
        failed_roles: list[discord.Role],
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
                role_list = [
                    role.mention + " "
                    for role in item.added
                    if int(role.id) not in map(lambda x: x.id, failed_roles)
                ]
                if not role_list:
                    continue
                added_chunks.append(link_title)
                added_chunks.extend(role_list)
                added_chunks.append("\n")
            if item.removed:
                role_list = [
                    role.mention + " "
                    for role in item.removed
                    if int(role.id) not in map(lambda x: x.id, failed_roles)
                ]
                if not role_list:
                    continue
                removed_chunks.append(link_title)
                removed_chunks.extend(role_list)
                removed_chunks.append("\n")

        added_content = "".join(added_chunks).strip()
        removed_content = "".join(removed_chunks).strip()

        return added_content, removed_content

    async def log_join(
        self,
        user_channel: LinkableChannel,
        member: discord.Member,
        roles_changed: list[VoiceStateReturnData],
        failed_roles: list[discord.Role],
    ) -> None:
        guild_data = await self.client.db.get_guild_data(member.guild.id)

        if not guild_data.logging:
            return

        logging_embed = discord.Embed(
            title=f"Member joined {'voice' if isinstance(user_channel, discord.VoiceChannel) else 'stage' if isinstance(user_channel, discord.StageChannel) else ''} channel",
            description=f"{member} joined {user_channel.mention}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )

        logging_embed.set_footer(text=f"User ID - {member.id}")
        logging_embed.set_author(
            name=member.name, icon_url=member.avatar.url if member.avatar else None
        )

        added_content, removed_content = self.construct_embed(
            roles_changed, failed_roles
        )

        if added_content:
            logging_embed.add_field(
                name="Roles Added:", value=added_content, inline=False
            )
        if removed_content:
            logging_embed.add_field(
                name="Roles Removed:", value=removed_content, inline=False
            )
        if failed_roles:
            logging_embed.add_field(
                name="Failed Roles:",
                value=" ".join([role.mention for role in failed_roles]),
                inline=False,
            )

        await self.add_to_queue(member.guild.id, logging_embed)

    async def log_leave(
        self,
        user_channel: LinkableChannel,
        member: discord.Member,
        roles_changed: list[VoiceStateReturnData],
        failed_roles: list[discord.Role],
    ) -> None:
        guild_data = await self.client.db.get_guild_data(member.guild.id)

        if not guild_data.logging:
            return

        logging_embed = discord.Embed(
            title=f"Member left {'voice' if isinstance(user_channel, discord.VoiceChannel) else 'stage' if isinstance(user_channel, discord.StageChannel) else ''} channel",
            description=f"{member} left {user_channel.mention}",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        logging_embed.set_footer(text=f"User ID - {member.id}")
        logging_embed.set_author(
            name=member.name, icon_url=member.avatar.url if member.avatar else None
        )

        added_content, removed_content = self.construct_embed(
            roles_changed, failed_roles
        )

        if added_content:
            logging_embed.add_field(
                name="Roles Added:", value=added_content, inline=False
            )
        if removed_content:
            logging_embed.add_field(
                name="Roles Removed:", value=removed_content, inline=False
            )
        if failed_roles:
            logging_embed.add_field(
                name="Failed Roles:",
                value=" ".join([role.mention for role in failed_roles]),
                inline=False,
            )

        await self.add_to_queue(member.guild.id, logging_embed)

    async def log_change(
        self,
        user_before_channel: LinkableChannel,
        user_after_channel: LinkableChannel,
        member: discord.Member,
        leave_roles_changed: list[VoiceStateReturnData],
        join_roles_changed: list[VoiceStateReturnData],
        failed_roles: list[discord.Role],
    ):
        guild_data = await self.client.db.get_guild_data(member.guild.id)

        if not guild_data.logging:
            return

        logging_embed = discord.Embed(
            title="Member moved channel",
            description=f"**Before:** {user_before_channel.mention}\n**+After:** {user_after_channel.mention}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        logging_embed.set_footer(text=f"User ID - {member.id}")
        logging_embed.set_author(
            name=member.name, icon_url=member.avatar.url if member.avatar else None
        )

        for i in leave_roles_changed:
            matching = [
                j
                for j in join_roles_changed
                if set(map(lambda x: str(x.id), i.added))
                == set(map(lambda x: str(x.id), j.removed))
                and set(map(lambda x: str(x.id), i.removed))
                == set(map(lambda x: str(x.id), j.added))
                and i.link_type == j.link_type
            ]
            if matching:
                leave_roles_changed.remove(i)
                join_roles_changed.remove(matching[0])

        added_content, removed_content = self.construct_embed(
            leave_roles_changed, failed_roles
        )

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

        added_content, removed_content = self.construct_embed(
            join_roles_changed, failed_roles
        )

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

        if failed_roles:
            logging_embed.add_field(
                name="Failed Roles:",
                value=" ".join([role.mention for role in failed_roles]),
                inline=False,
            )

        await self.add_to_queue(member.guild.id, logging_embed)
