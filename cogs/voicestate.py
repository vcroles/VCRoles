import asyncio
from asyncio import Task
from typing import Optional

import discord
from discord.ext import commands
from prisma.enums import LinkType
from prisma.models import Link

from utils import VCRolesClient
from utils.types import (
    DiscordID,
    MentionableRole,
    RoleList,
    VoiceStateData,
    VoiceStateReturnData,
)
from utils.utils import add_suffix, remove_suffix
from voicestate import Generator, Logging


class VoiceState(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.generator = Generator(client)
        self.logging = Logging(client)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        # Joining
        if not before.channel and after.channel:
            roles_changed = await self.join(member, after)

            if roles_changed:
                await self.logging.log_join(
                    after.channel,
                    member,
                    roles_changed,
                )

        # Leaving
        elif before.channel and not after.channel:
            roles_changed = await self.leave(member, before)

            if roles_changed:
                await self.logging.log_leave(
                    before.channel,
                    member,
                    roles_changed,
                )

        # Changing
        elif before.channel and after.channel and before.channel != after.channel:

            leave_roles_changed = await self.leave(member, before)

            join_roles_changed = await self.join(member, after)

            if leave_roles_changed and join_roles_changed:
                await self.logging.log_change(
                    before.channel,
                    after.channel,
                    member,
                    leave_roles_changed,
                    join_roles_changed,
                )

        if (
            isinstance(before.channel, discord.StageChannel)
            and isinstance(after.channel, discord.StageChannel)
            and before.channel.id == after.channel.id
        ):
            # Become Speaker
            if before.suppress and not after.suppress:
                data = await self.client.db.get_channel_linked(
                    before.channel.id, member.guild.id, LinkType.STAGE
                )

                for role_id in data.speakerRoles:
                    role = member.guild.get_role(int(role_id))
                    if not role:
                        continue

                    try:
                        await member.add_roles(role, reason="Became Speaker")
                    except discord.errors.Forbidden:
                        pass
                    except discord.errors.HTTPException:
                        pass

            # Stop Speaker
            elif not before.suppress and after.suppress:
                data = await self.client.db.get_channel_linked(
                    before.channel.id, member.guild.id, LinkType.STAGE
                )

                for role_id in data.speakerRoles:
                    role = member.guild.get_role(int(role_id))
                    if not role:
                        continue

                    try:
                        await member.remove_roles(role, reason="Stopped Speaker")
                    except discord.errors.Forbidden:
                        pass
                    except discord.errors.HTTPException:
                        pass

    @staticmethod
    def data_converter(
        links: list[Link], channel_id: DiscordID, category_id: Optional[DiscordID]
    ) -> VoiceStateData:
        return_data = VoiceStateData()

        for link in links:
            if link.type == LinkType.REGULAR:
                return_data.voice_data = link
            elif link.type == LinkType.STAGE:
                return_data.stage_data = link
            elif link.type == LinkType.CATEGORY:
                return_data.category_data = link
            elif link.type == LinkType.PERMANENT:
                if link.id == str(channel_id):
                    return_data.permanent_data = link
                elif category_id and link.id == str(category_id):
                    return_data.category_perm_data = link
            elif link.type == LinkType.ALL:
                return_data.all_data = link

        return_data.suffix = " ".join(
            list(
                filter(
                    None,
                    [
                        i.suffix if i and i.suffix else ""
                        for i in [
                            return_data.voice_data,
                            return_data.stage_data,
                            return_data.category_data,
                            return_data.all_data,
                        ]
                    ],
                )
            )
        )

        return return_data

    async def join(
        self,
        member: discord.Member,
        after: discord.VoiceState,
    ) -> list[VoiceStateReturnData]:
        if not after.channel or not after.channel.type:
            return []

        links = await self.client.db.get_all_linked_channel(
            member.guild.id,
            after.channel.id,
            after.channel.category.id if after.channel.category else None,
        )

        linked_data = self.data_converter(
            links,
            after.channel.id,
            after.channel.category.id if after.channel.category else None,
        )

        tasks: list[Task[VoiceStateReturnData]] = []

        if isinstance(after.channel, discord.VoiceChannel) and linked_data.voice_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(linked_data.voice_data, member, after.channel.id)
                )
            )

        if isinstance(after.channel, discord.StageChannel) and linked_data.stage_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(linked_data.stage_data, member, after.channel.id)
                )
            )

        if after.channel.category and linked_data.category_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(
                        linked_data.category_data,
                        member,
                        after.channel.id,
                    )
                )
            )

        if after.channel.category and linked_data.category_perm_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(
                        linked_data.category_perm_data,
                        member,
                        after.channel.id,
                    )
                )
            )

        if linked_data.permanent_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(
                        linked_data.permanent_data,
                        member,
                        after.channel.id,
                    )
                )
            )

        if linked_data.all_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(linked_data.all_data, member, after.channel.id)
                )
            )

        await self.generator.join(member, after.channel)

        await add_suffix(member, linked_data.suffix)

        results: list[VoiceStateReturnData] = await asyncio.gather(*tasks)

        return results

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
    ) -> list[VoiceStateReturnData]:
        if not before.channel or not before.channel.type:
            return []

        links = await self.client.db.get_all_linked_channel(
            member.guild.id,
            before.channel.id,
            before.channel.category.id if before.channel.category else None,
        )

        linked_data = self.data_converter(
            links,
            before.channel.id,
            before.channel.category.id if before.channel.category else None,
        )

        tasks: list[Task[VoiceStateReturnData]] = []

        if linked_data.all_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(linked_data.all_data, member, before.channel.id)
                )
            )

        if before.channel.category and linked_data.category_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(
                        linked_data.category_data,
                        member,
                        before.channel.id,
                    )
                )
            )

        if isinstance(before.channel, discord.StageChannel) and linked_data.stage_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(
                        linked_data.stage_data,
                        member,
                        before.channel.id,
                    )
                )
            )

        if isinstance(before.channel, discord.VoiceChannel) and linked_data.voice_data:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(
                        linked_data.voice_data,
                        member,
                        before.channel.id,
                    )
                )
            )

        await self.generator.leave(member, before.channel)

        await remove_suffix(member, linked_data.suffix)

        results: list[VoiceStateReturnData] = await asyncio.gather(*tasks)

        return results

    async def handle_join(
        self,
        data: Link,
        member: discord.Member,
        channel_id: DiscordID,
    ) -> VoiceStateReturnData:
        if str(channel_id) in data.excludeChannels:
            return VoiceStateReturnData("join", data.type)

        if data.type == LinkType.PERMANENT and data.suffix:
            await add_suffix(member, data.suffix)

        added: RoleList = []
        for role_id in data.linkedRoles:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Joined voice channel")
                except discord.errors.Forbidden:
                    pass
                except discord.errors.HTTPException:
                    pass
            else:
                role = MentionableRole(role_id)
            added.append(role)

        removed: RoleList = []
        for role_id in data.reverseLinkedRoles:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.remove_roles(role, reason="Joined voice channel")
                except discord.errors.Forbidden:
                    pass
                except discord.errors.HTTPException:
                    pass
            else:
                role = MentionableRole(role_id)
            removed.append(role)

        self.client.incr_role_counter("added", len(added))
        self.client.incr_role_counter("removed", len(removed))

        return VoiceStateReturnData("join", data.type, added, removed)

    async def handle_leave(
        self,
        data: Link,
        member: discord.Member,
        channel_id: DiscordID,
    ) -> VoiceStateReturnData:
        if str(channel_id) in data.excludeChannels:
            return VoiceStateReturnData("leave", data.type)

        if data.type == LinkType.PERMANENT and data.suffix:
            await remove_suffix(member, data.suffix)

        added: RoleList = []
        for role_id in data.reverseLinkedRoles:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.add_roles(role, reason="Left voice channel")
                except discord.errors.Forbidden:
                    pass
                except discord.errors.HTTPException:
                    pass
            else:
                role = MentionableRole(role_id)
            added.append(role)

        removed: RoleList = []
        for role_id in data.linkedRoles:
            role = member.guild.get_role(int(role_id))
            if role:
                try:
                    await member.remove_roles(role, reason="Left voice channel")
                except discord.errors.Forbidden:
                    pass
                except discord.errors.HTTPException:
                    pass
            else:
                role = MentionableRole(role_id)
            removed.append(role)

        self.client.incr_role_counter("added", len(added))
        self.client.incr_role_counter("removed", len(removed))

        return VoiceStateReturnData("leave", data.type, added, removed)


async def setup(client: VCRolesClient):
    await client.add_cog(VoiceState(client))
