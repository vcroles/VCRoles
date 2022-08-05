import discord
from discord import app_commands
from discord.ext import commands

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient


class Linked(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    def construct_linked_content(
        self, data: dict, interaction: discord.Interaction
    ) -> str:
        chunks = []
        for channel_id, channel_data in data.items():
            if channel_id == "format":
                continue
            try:
                channel = self.client.get_channel(int(channel_id))
                chunks.append(f"{channel.mention}: ")
                chunks.append(self.iterate_links(channel_data, interaction))
            except:
                chunks.append(f"Not Found - ID `{channel_id}`\n")

        return "".join(chunks)

    def iterate_links(
        self, channel_data: dict, interaction: discord.Interaction
    ) -> str:
        """
        Iterates through:
        - Roles
        - Reverse Roles
        - Suffix
        """
        chunks = []

        for role_id in channel_data["roles"]:
            role = interaction.guild.get_role(int(role_id))
            chunks.append(f"{role.mention if role else role_id}, ")

        for role_id in channel_data["reverse_roles"]:
            role = interaction.guild.get_role(int(role_id))
            chunks.append(f"R{role.mention if role else role_id}, ")

        chunks.append(f"`{channel_data['suffix']}`" if channel_data["suffix"] else "")

        content = "".join(chunks)

        content = content.removesuffix(", ") + "\n"

        return content

    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def linked(self, interaction: discord.Interaction):
        """Displays the linked roles, channels & categories"""

        linked_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"The linked roles, channels & categories in {interaction.guild.name}:",
            description="Note: \n- R before a role indicates a reverse link\n- Text like `this` shows linked suffixes",
        )

        for channel_type in ["Voice", "Stage", "Category", "Permanent"]:
            content = self.construct_linked_content(
                self.client.redis.get_linked(
                    channel_type.lower(), interaction.guild_id
                ),
                interaction,
            )

            if content:
                linked_embed.add_field(
                    name=f"{channel_type} Channels:", value=content, inline=False
                )

        all_dict = self.client.redis.get_linked("all", interaction.guild_id)

        all_content = self.iterate_links(all_dict, interaction)

        chunks = [all_content]

        if "except" in all_dict:
            if all_dict["except"]:
                chunks.append("All-link exceptions: ")
                for exception_id in all_dict["except"]:
                    try:
                        channel = self.client.get_channel(int(exception_id))
                        chunks.append(f"{channel.mention}, ")
                    except:
                        chunks.append(f"Not Found - ID `{exception_id}`")

        all_content = "".join(chunks).removesuffix(", ")

        if all_content.strip():
            linked_embed.add_field(
                name="All Link:", value=all_content.strip(), inline=False
            )

        if linked_embed.fields:
            await interaction.response.send_message(embed=linked_embed)
        else:
            await interaction.response.send_message("Nothing is linked")

        return self.client.incr_counter("linked")


async def setup(client: VCRolesClient):
    await client.add_cog(Linked(client))
