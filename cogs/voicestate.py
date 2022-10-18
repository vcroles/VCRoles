import asyncio
from asyncio import Task
from typing import Optional

import discord
from discord.ext import commands
from prisma.enums import LinkType

from utils import VCRolesClient
from utils.types import DiscordID, MentionableRole, RoleList, VoiceStateReturnData
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
            roles_changed = await self.join(member, before, after)

            if roles_changed:
                await self.logging.log_join(
                    after,
                    member,
                    roles_changed,
                )

        # Leaving
        elif before.channel and not after.channel:
            roles_changed = await self.leave(member, before, after)

            if roles_changed:
                await self.logging.log_leave(
                    before,
                    member,
                    roles_changed,
                )

        # Changing
        elif before.channel != after.channel:

            leave_roles_changed = await self.leave(member, before, after)

            join_roles_changed = await self.join(member, before, after)

            if leave_roles_changed and join_roles_changed:
                await self.logging.log_change(
                    before,
                    after,
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

    async def join(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list[VoiceStateReturnData]:
        if not after.channel or not after.channel.type:
            return []

        tasks: list[Task[VoiceStateReturnData]] = []

        if isinstance(after.channel, discord.VoiceChannel):
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(LinkType.REGULAR, member, after.channel.id)
                )
            )

        if isinstance(after.channel, discord.StageChannel):
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(LinkType.STAGE, member, after.channel.id)
                )
            )

        if after.channel.category:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(
                        LinkType.CATEGORY,
                        member,
                        after.channel.id,
                        after.channel.category.id,
                    )
                )
            )
            tasks.append(
                self.client.loop.create_task(
                    self.handle_join(
                        LinkType.PERMANENT,
                        member,
                        after.channel.id,
                        after.channel.category.id,
                    )
                )
            )

        tasks.append(
            self.client.loop.create_task(
                self.handle_join(LinkType.ALL, member, after.channel.id)
            )
        )

        tasks.append(
            self.client.loop.create_task(
                self.handle_join(
                    LinkType.PERMANENT,
                    member,
                    after.channel.id,
                )
            )
        )

        await self.generator.join(member, before, after)

        results: list[VoiceStateReturnData] = await asyncio.gather(*tasks)

        return results

    async def leave(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> list[VoiceStateReturnData]:
        if not before.channel or not before.channel.type:
            return []

        tasks: list[Task[VoiceStateReturnData]] = []

        tasks.append(
            self.client.loop.create_task(
                self.handle_leave(LinkType.ALL, member, before.channel.id)
            )
        )

        if before.channel.category:
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(
                        LinkType.CATEGORY,
                        member,
                        before.channel.id,
                        before.channel.category.id,
                    )
                )
            )

        if isinstance(before.channel, discord.StageChannel):
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(
                        LinkType.STAGE,
                        member,
                        before.channel.id,
                    )
                )
            )

        if isinstance(before.channel, discord.VoiceChannel):
            tasks.append(
                self.client.loop.create_task(
                    self.handle_leave(
                        LinkType.REGULAR,
                        member,
                        before.channel.id,
                    )
                )
            )

        await self.generator.leave(member, before, after)

        results: list[VoiceStateReturnData] = await asyncio.gather(*tasks)

        return results

    async def handle_join(
        self,
        link_type: LinkType,
        member: discord.Member,
        channel_id: DiscordID,
        category_id: Optional[DiscordID] = None,
    ) -> VoiceStateReturnData:
        if link_type == LinkType.ALL:
            data = await self.client.db.get_channel_linked(
                member.guild.id, member.guild.id, link_type
            )
        elif category_id:
            data = await self.client.db.get_channel_linked(
                category_id, member.guild.id, link_type
            )
        else:
            data = await self.client.db.get_channel_linked(
                channel_id, member.guild.id, link_type
            )

        if str(channel_id) in data.excludeChannels:
            return VoiceStateReturnData("join", data.type)

        if data.suffix:
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
        link_type: LinkType,
        member: discord.Member,
        channel_id: DiscordID,
        category_id: Optional[DiscordID] = None,
    ) -> VoiceStateReturnData:
        if link_type == LinkType.ALL:
            data = await self.client.db.get_channel_linked(
                member.guild.id, member.guild.id, link_type
            )
        elif category_id:
            data = await self.client.db.get_channel_linked(
                category_id, member.guild.id, link_type
            )
        else:
            data = await self.client.db.get_channel_linked(
                channel_id, member.guild.id, link_type
            )

        if str(channel_id) in data.excludeChannels:
            return VoiceStateReturnData("leave", data.type)

        if data.suffix:
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
