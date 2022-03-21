import discord
from discord.commands import slash_command
from discord.ext import commands

from bot import MyClient
from utils import Permissions


class Linked(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    def construct_linked_content(
        self, data: dict, ctx: discord.ApplicationContext
    ) -> str:
        content = ""
        for channel_id, channel_data in data.items():
            if channel_id == "format":
                continue
            try:
                channel = self.client.get_channel(int(channel_id))
                content += f"{channel.mention}: "
                content += self.iterate_links(channel_data, ctx)
            except:
                content += f"Not Found - ID `{channel_id}`\n"

        return content

    def iterate_links(self, channel_data: dict, ctx: discord.ApplicationContext) -> str:
        """
        Iterates through:
        - Roles
        - Reverse Roles
        - Suffix
        """
        content = ""
        for role_id in channel_data["roles"]:
            try:
                role = ctx.guild.get_role(int(role_id))
                content += f"{role.mention}, "
            except:
                pass
        for role_id in channel_data["reverse_roles"]:
            try:
                role = ctx.guild.get_role(int(role_id))
                content += f"{role.mention}, "
            except:
                pass
        content += f"`{channel_data['suffix']}`" if channel_data["suffix"] else ""
        content = content.removesuffix(", ") + "\n"
        return content

    @slash_command(description="Displays the linked roles, channels & categories")
    @Permissions.has_permissions(administrator=True)
    async def linked(self, ctx: discord.ApplicationContext):

        linked_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"The linked roles, channels & categories in {ctx.guild.name}:",
            description="Note: \n- R before a role indicates a reverse link\n- Text like `this` shows linked suffixes",
        )

        for channel_type in ["Voice", "Stage", "Category", "Permanent"]:
            content = self.construct_linked_content(
                self.client.redis.get_linked(channel_type.lower(), ctx.guild.id), ctx
            )
            if content:
                linked_embed.add_field(
                    name=f"{channel_type} Channels:", value=content, inline=False
                )

        all_dict = self.client.redis.get_linked("all", ctx.guild.id)

        all_content = self.iterate_links(all_dict, ctx)

        if all_dict["except"]:
            all_content += "All-link exceptions: "
            for exception_id in all_dict["except"]:
                try:
                    channel = self.client.get_channel(int(exception_id))
                    all_content += f"{channel.mention}, "
                except:
                    all_content += f"Not Found - ID `{exception_id}`"
            all_content = all_content.removesuffix(", ")
        if all_content:
            linked_embed.add_field(
                name="All Link:", value=all_content.strip(), inline=False
            )

        if len(linked_embed.fields) > 0:
            await ctx.respond(embed=linked_embed)
        else:
            await ctx.respond("Nothing is linked")


def setup(client: MyClient):
    client.add_cog(Linked(client))
