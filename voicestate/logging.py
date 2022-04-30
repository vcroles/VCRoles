import datetime

import discord

from bot import MyClient
from utils import ReturnData


class Logging:
    def __init__(self, client: MyClient):
        self.client = client

    def construct_embed(
        self,
        voice_changed: dict[str, list],
        stage_changed: dict[str, list],
        category_changed: dict[str, list],
        all_changed: dict[str, list] = None,
        perm_changed: dict[str, list] = None,
    ):

        added_chunks = []
        removed_chunks = []

        # Voice
        if voice_changed["added"]:
            added_chunks.append("Channel: ")
            added_chunks.extend([role.mention + " " for role in voice_changed["added"]])
            added_chunks.append("\n")
        if voice_changed["removed"]:
            removed_chunks.append("Channel: ")
            removed_chunks.extend(
                [role.mention + " " for role in voice_changed["removed"]]
            )
            removed_chunks.append("\n")

        # Stage
        if stage_changed["added"]:
            added_chunks.append("Channel: ")
            added_chunks.extend([role.mention + " " for role in stage_changed["added"]])
            added_chunks.append("\n")
        if stage_changed["removed"]:
            removed_chunks.append("Channel: ")
            removed_chunks.extend(
                [role.mention + " " for role in stage_changed["removed"]]
            )
            removed_chunks.append("\n")

        # Category
        if category_changed["added"]:
            added_chunks.append("Category: ")
            added_chunks.extend(
                [role.mention + " " for role in category_changed["added"]]
            )
            added_chunks.append("\n")
        if category_changed["removed"]:
            removed_chunks.append("Category: ")
            removed_chunks.extend(
                [role.mention + " " for role in category_changed["removed"]]
            )
            removed_chunks.append("\n")

        # All
        if all_changed:
            if all_changed["added"]:
                added_chunks.append("All: ")
                added_chunks.extend(
                    [role.mention + " " for role in all_changed["added"]]
                )
                added_chunks.append("\n")
            if all_changed["removed"]:
                removed_chunks.append("All: ")
                removed_chunks.extend(
                    [role.mention + " " for role in all_changed["removed"]]
                )
                removed_chunks.append("\n")

        # Permanent
        if perm_changed:
            if perm_changed["added"]:
                added_chunks.append("Permanent: ")
                added_chunks.extend(
                    [role.mention + " " for role in perm_changed["added"]]
                )
                added_chunks.append("\n")
            if perm_changed["removed"]:
                removed_chunks.append("Permanent: ")
                removed_chunks.extend(
                    [role.mention + " " for role in perm_changed["removed"]]
                )
                removed_chunks.append("\n")

        added_content = "".join(added_chunks).strip()
        removed_content = "".join(removed_chunks).strip()

        return added_content, removed_content

    async def log_join(
        self,
        after: discord.VoiceState,
        member: discord.Member,
        roles_changed: ReturnData,
    ):
        data = self.client.redis.get_guild_data(member.guild.id)

        if data["logging"] != "None":
            try:
                channel = data["logging"]
                channel = self.client.get_channel(int(channel))
                if channel not in member.guild.channels:
                    return
                logging_embed = discord.Embed(
                    title=f"Member joined {'voice' if isinstance(after.channel, discord.VoiceChannel) else 'stage' if isinstance(after.channel, discord.StageChannel) else ''} channel",
                    description=f"{member} joined {after.channel.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                logging_embed.set_footer(text=f"User ID - {member.id}")
                logging_embed.set_author(
                    name=f"{member.name}#{member.discriminator}",
                    icon_url=member.avatar.url,
                )

                added_content, removed_content = self.construct_embed(
                    roles_changed.voice_changed,
                    roles_changed.stage_changed,
                    roles_changed.category_changed,
                    roles_changed.all_changed,
                    roles_changed.perm_changed,
                )

                if added_content:
                    logging_embed.add_field(
                        name="Roles Added:", value=added_content, inline=False
                    )
                if removed_content:
                    logging_embed.add_field(
                        name="Roles Removed:", value=removed_content, inline=False
                    )

                await channel.send(embed=logging_embed)
            except:
                return

    async def log_leave(
        self,
        before: discord.VoiceState,
        member: discord.Member,
        roles_changed: ReturnData,
    ):
        data = self.client.redis.get_guild_data(member.guild.id)

        if data["logging"] != "None":
            try:
                channel = data["logging"]
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(
                    title=f"Member left {'voice' if isinstance(before.channel, discord.VoiceChannel) else 'stage' if isinstance(before.channel, discord.StageChannel) else ''} channel",
                    description=f"{member} left {before.channel.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                logging_embed.set_footer(text=f"User ID - {member.id}")
                logging_embed.set_author(
                    name=f"{member.name}#{member.discriminator}",
                    icon_url=member.avatar.url,
                )

                added_content, removed_content = self.construct_embed(
                    roles_changed.voice_changed,
                    roles_changed.stage_changed,
                    roles_changed.category_changed,
                    roles_changed.all_changed,
                )

                if added_content:
                    logging_embed.add_field(
                        name="Roles Added:", value=added_content, inline=False
                    )
                if removed_content:
                    logging_embed.add_field(
                        name="Roles Removed:", value=removed_content, inline=False
                    )

                await channel.send(embed=logging_embed)
            except:
                return

    async def log_change(
        self,
        before: discord.VoiceState,
        after: discord.VoiceState,
        member: discord.Member,
        leave_roles_changed: ReturnData,
        join_roles_changed: ReturnData,
    ):
        data = self.client.redis.get_guild_data(member.guild.id)

        if data["logging"] != "None":
            try:
                channel = data["logging"]
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(
                    title=f"Member moved channel",
                    description=f"**Before:** {before.channel.mention}\n**+After:** {after.channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.now(datetime.timezone.utc),
                )
                logging_embed.set_footer(text=f"User ID - {member.id}")
                logging_embed.set_author(
                    name=f"{member.name}#{member.discriminator}",
                    icon_url=member.avatar.url,
                )

                added_content, removed_content = self.construct_embed(
                    leave_roles_changed.voice_changed,
                    leave_roles_changed.stage_changed,
                    leave_roles_changed.category_changed,
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
                    join_roles_changed.voice_changed,
                    join_roles_changed.stage_changed,
                    join_roles_changed.category_changed,
                    perm_changed=join_roles_changed.perm_changed,
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

                await channel.send(embed=logging_embed)

            except:
                return
