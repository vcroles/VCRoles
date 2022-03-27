import datetime

import discord

from bot import MyClient


class Logging:
    def __init__(self, client: MyClient):
        self.client = client

    def construct_embed(
        self,
        voice_changed: dict[str, list],
        stage_changed: dict[str, list],
        category_changed: dict[str, list],
        all_changed: dict[str, list] | None = None,
        perm_changed: dict[str, list] | None = None,
    ):
        added_content = ""
        removed_content = ""

        # Voice
        if voice_changed["added"]:
            added_content += "Channel: "
            for role in voice_changed["added"]:
                added_content += role.mention + " "
            added_content += "\n"
        if voice_changed["removed"]:
            removed_content += "Channel: "
            for role in voice_changed["removed"]:
                removed_content += role.mention + " "
            removed_content += "\n"

        # Stage
        if stage_changed["added"]:
            added_content += "Channel: "
            for role in stage_changed["added"]:
                added_content += role.mention + " "
            added_content += "\n"
        if stage_changed["removed"]:
            removed_content += "Channel: "
            for role in stage_changed["removed"]:
                removed_content += role.mention + " "
            removed_content += "\n"

        # Category
        if category_changed["added"]:
            added_content += "Category: "
            for role in category_changed["added"]:
                added_content += role.mention + " "
            added_content += "\n"
        if category_changed["removed"]:
            removed_content += "Category: "
            for role in category_changed["removed"]:
                removed_content += role.mention + " "
            removed_content += "\n"

        # All
        if all_changed:
            if all_changed["added"]:
                added_content += "All: "
                for role in all_changed["added"]:
                    added_content += role.mention + " "
                added_content += "\n"
            if all_changed["removed"]:
                removed_content += "All: "
                for role in all_changed["removed"]:
                    removed_content += role.mention + " "
                removed_content += "\n"

        # Permanent
        if perm_changed:
            if perm_changed["added"]:
                added_content += "Permissions: "
                for role in perm_changed["added"]:
                    added_content += role.mention + " "
                added_content += "\n"
            if perm_changed["removed"]:
                removed_content += "Permissions: "
                for role in perm_changed["removed"]:
                    removed_content += role.mention + " "
                removed_content += "\n"

        if added_content:
            added_content = added_content[:-1]  # Removes trailing newline
        if removed_content:
            removed_content = removed_content[:-1]

        return added_content, removed_content

    async def log_join(
        self,
        after: discord.VoiceState,
        member: discord.Member,
        voice_changed: dict[str, list],
        stage_changed: dict[str, list],
        category_changed: dict[str, list],
        all_changed: dict[str, list],
        perm_changed: dict[str, list],
    ):
        data = self.client.redis.get_guild_data(member.guild.id)

        if data["logging"] != "None":
            try:
                channel = data["logging"]
                channel = self.client.get_channel(int(channel))
                if channel not in member.guild.channels:
                    return
                logging_embed = discord.Embed(
                    title=f"Member joined voice channel",
                    description=f"{member} joined {after.channel.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.utcnow(),
                )
                logging_embed.set_footer(text=f"User ID - {member.id}")
                logging_embed.set_author(
                    name=f"{member.name}#{member.discriminator}",
                    icon_url=member.avatar.url,
                )

                added_content, removed_content = self.construct_embed(
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                    perm_changed,
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
        voice_changed: dict[str, list],
        stage_changed: dict[str, list],
        category_changed: dict[str, list],
        all_changed: dict[str, list],
    ):
        data = self.client.redis.get_guild_data(member.guild.id)

        if data["logging"] != "None":
            try:
                channel = data["logging"]
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(
                    title=f"Member left voice channel",
                    description=f"{member} left {before.channel.mention}",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.utcnow(),
                )
                logging_embed.set_footer(text=f"User ID - {member.id}")
                logging_embed.set_author(
                    name=f"{member.name}#{member.discriminator}",
                    icon_url=member.avatar.url,
                )

                added_content, removed_content = self.construct_embed(
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
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
        leave_roles_changed: tuple,
        join_roles_changed: tuple,
    ):
        data = self.client.redis.get_guild_data(member.guild.id)

        if data["logging"] != "None":
            try:
                channel = data["logging"]
                channel = self.client.get_channel(int(channel))
                logging_embed = discord.Embed(
                    title=f"Member moved voice channel",
                    description=f"**Before:** {before.channel.mention}\n**+After:** {after.channel.mention}",
                    color=discord.Color.blue(),
                    timestamp=datetime.datetime.utcnow(),
                )
                logging_embed.set_footer(text=f"User ID - {member.id}")
                logging_embed.set_author(
                    name=f"{member.name}#{member.discriminator}",
                    icon_url=member.avatar.url,
                )

                (
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                ) = leave_roles_changed

                added_content, removed_content = self.construct_embed(
                    voice_changed,
                    stage_changed,
                    category_changed,
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

                (
                    voice_changed,
                    stage_changed,
                    category_changed,
                    all_changed,
                    perm_changed,
                ) = join_roles_changed

                added_content, removed_content = self.construct_embed(
                    voice_changed,
                    stage_changed,
                    category_changed,
                    perm_changed=perm_changed,
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
