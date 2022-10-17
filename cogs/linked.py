from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
from prisma.enums import LinkType
from prisma.models import Link

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from utils.types import LinkableChannel


class Linked(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    def iterate_links(
        self,
        interaction: discord.Interaction,
        roles: list[str],
        reverse: list[str],
        speaker: list[str],
        suffix: Optional[str],
    ) -> str:
        chunks: list[str] = []
        if not interaction.guild:
            return ""

        for role_id in roles:
            role = interaction.guild.get_role(int(role_id))
            chunks.append(f"{role.mention if role else role_id}, ")

        for role_id in reverse:
            role = interaction.guild.get_role(int(role_id))
            chunks.append(f"R{role.mention if role else role_id}, ")

        for role_id in speaker:
            role = interaction.guild.get_role(int(role_id))
            chunks.append(f"S{role.mention if role else role_id}, ")

        chunks.append(f"`{suffix}`" if suffix else "")

        content = "".join(chunks)

        content = content.removesuffix(", ") + "\n"

        return content

    def iterate_channels(self, exclude_channels: list[str]) -> str:
        chunks: list[str] = ["Excluded Channels: "]
        for channel_id in exclude_channels:
            channel = self.client.get_channel(int(channel_id))
            if not isinstance(channel, LinkableChannel):
                chunks.append(f"{channel_id}, ")
                continue
            chunks.append(f"{channel.mention}, ")
        if len(chunks) == 1:
            return "\n"
        return "".join(chunks).removesuffix(", ") + "\n"

    def construct_linked_content(
        self, interaction: discord.Interaction, link: Link
    ) -> str:
        chunks: list[str] = []
        channel = self.client.get_channel(int(link.id))
        if link.type == LinkType.ALL:
            chunks.append(
                self.iterate_links(
                    interaction,
                    link.linkedRoles,
                    link.reverseLinkedRoles,
                    link.speakerRoles,
                    link.suffix,
                )
            )
            exclude_content = self.iterate_channels(link.excludeChannels)
            chunks.append(exclude_content)
        elif not channel or not isinstance(channel, LinkableChannel):
            chunks.append(f"Not Found - ID `{link.id}`\n")
        else:
            chunks.append(f"{channel.mention}: ")
            chunks.append(
                self.iterate_links(
                    interaction,
                    link.linkedRoles,
                    link.reverseLinkedRoles,
                    link.speakerRoles,
                    link.suffix,
                )
            )
            if link.type == LinkType.CATEGORY:
                exclude_content = self.iterate_channels(link.excludeChannels)
                chunks.append(exclude_content)

        return "".join(chunks)

    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def linked(self, interaction: discord.Interaction):
        """Displays the linked roles, channels & categories"""
        if not interaction.guild_id or not interaction.guild:
            return await interaction.response.send_message(
                "You must use this command in a guild."
            )

        linked_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"The linked roles, channels & categories in {interaction.guild.name}:",
            description="Note: \n- R before a role indicates a reverse link\n- Text like `this` shows linked suffixes",
        )

        links = await self.client.db.get_all_linked(interaction.guild_id)

        voice_chunks: list[str] = []
        stage_chunks: list[str] = []
        category_chunks: list[str] = []
        permanent_chunks: list[str] = []
        all_chunks: list[str] = []

        for link in links:
            content = self.construct_linked_content(interaction, link)
            if link.type == LinkType.REGULAR:
                voice_chunks.append(content)
            elif link.type == LinkType.STAGE:
                stage_chunks.append(content)
            elif link.type == LinkType.CATEGORY:
                category_chunks.append(content)
            elif link.type == LinkType.PERMANENT:
                permanent_chunks.append(content)
            elif link.type == LinkType.ALL:
                all_chunks.append(content)

        voice_content = "".join(voice_chunks).strip()
        stage_content = "".join(stage_chunks).strip()
        category_content = "".join(category_chunks).strip()
        permanent_content = "".join(permanent_chunks).strip()
        all_content = "".join(all_chunks).strip()

        if voice_content:
            linked_embed.add_field(
                name="Voice Channels:", value=voice_content, inline=False
            )
        if stage_content:
            linked_embed.add_field(
                name="Stage Channels:", value=stage_content, inline=False
            )
        if category_content:
            linked_embed.add_field(
                name="Category Channels:", value=category_content, inline=False
            )
        if permanent_content:
            linked_embed.add_field(
                name="Permanent Channels:", value=permanent_content, inline=False
            )
        if all_content:
            linked_embed.add_field(name="All Link:", value=all_content, inline=False)

        if linked_embed.fields:
            await interaction.response.send_message(embed=linked_embed)
        else:
            await interaction.response.send_message("Nothing is linked")

        return self.client.incr_counter("linked")


async def setup(client: VCRolesClient):
    await client.add_cog(Linked(client))
