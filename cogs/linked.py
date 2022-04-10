import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class Linked(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    def construct_linked_content(
        self, data: dict, interaction: discord.Interaction
    ) -> str:
        content = ""
        for channel_id, channel_data in data.items():
            if channel_id == "format":
                continue
            try:
                channel = self.client.get_channel(int(channel_id))
                content += f"{channel.mention}: "
                content += self.iterate_links(channel_data, interaction)
            except:
                content += f"Not Found - ID `{channel_id}`\n"

        return content

    def iterate_links(
        self, channel_data: dict, interaction: discord.Interaction
    ) -> str:
        """
        Iterates through:
        - Roles
        - Reverse Roles
        - Suffix
        """
        content = ""
        for role_id in channel_data["roles"]:
            try:
                role = interaction.guild.get_role(int(role_id))
                content += f"{role.mention}, "
            except:
                pass
        for role_id in channel_data["reverse_roles"]:
            try:
                role = interaction.guild.get_role(int(role_id))
                content += f"R{role.mention}, "
            except:
                pass
        content += f"`{channel_data['suffix']}`" if channel_data["suffix"] else ""
        content = content.removesuffix(", ") + "\n"
        return content

    @app_commands.command(
        description="Displays the linked roles, channels & categories"
    )
    @Permissions.has_permissions(administrator=True)
    async def linked(self, interaction: discord.Interaction):

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

        if "except" in all_dict:
            if len(all_dict["except"]) > 0:
                all_content += "All-link exceptions: "
                for exception_id in all_dict["except"]:
                    try:
                        channel = self.client.get_channel(int(exception_id))
                        all_content += f"{channel.mention}, "
                    except:
                        all_content += f"Not Found - ID `{exception_id}`"
                all_content = all_content.removesuffix(", ")
        if all_content.strip():
            linked_embed.add_field(
                name="All Link:", value=all_content.strip(), inline=False
            )

        if len(linked_embed.fields) > 0:
            await interaction.response.send_message(embed=linked_embed)
        else:
            await interaction.response.send_message("Nothing is linked")

        return self.client.incr_counter("linked")


async def setup(client: MyClient):
    await client.add_cog(Linked(client))
