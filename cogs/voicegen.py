import json
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner
from views.interface import Interface


class VoiceGen(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    generator_commands = app_commands.Group(
        name="generator", description="Generator channel commands"
    )

    @generator_commands.command()
    @app_commands.describe(
        category_name="Name of generator category",
        voice_channel_name="Name of voice channel",
        interface_channel_name="Name of interface channel",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def create(
        self,
        interaction: discord.Interaction,
        category_name: Optional[str] = "Voice Generator",
        voice_channel_name: Optional[str] = "Voice Generator",
        interface_channel_name: Optional[str] = "VC Roles Interface",
    ):
        """Creates a voice channel generator"""

        if interaction.guild:
            assert isinstance(interaction.guild, discord.Guild)
        else:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )
        await interaction.response.defer()

        data = self.client.redis.get_generator(interaction.guild_id)

        try:
            data["interface"] = json.loads(data["interface"])
            channel = self.client.get_channel(int(data["interface"]["channel"]))
            msg = await channel.fetch_message(int(data["interface"]["msg_id"]))
            view = discord.ui.View.from_message(msg)
            view.clear_items()
            self.client.loop.create_task(msg.edit(view=view))
        except:
            pass

        category = await interaction.guild.create_category(name=category_name)

        voice_channel = await interaction.guild.create_voice_channel(
            name=voice_channel_name, category=category
        )

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                send_messages=False
            )
        }

        interface_channel = await interaction.guild.create_text_channel(
            name=interface_channel_name, category=category, overwrites=overwrites
        )

        interface_embed = discord.Embed(
            title="Voice Generator Interface",
            description=f"You can use this interface to customize your private voice channel.",
            color=discord.Color.blue(),
        )
        interface_embed.set_thumbnail(url=self.client.user.avatar.url)
        interface_embed.set_footer(text="Use these commands via the buttons below.")

        interface_embed.add_field(
            name="Lock",
            value="Stop people from joining your voice channel",
            inline=False,
        )
        interface_embed.add_field(
            name="Unlock", value="Allow people to join your voice channel", inline=False
        )
        interface_embed.add_field(
            name="Hide",
            value="Stop people from seeing your voice channel (in channel list)",
            inline=False,
        )
        interface_embed.add_field(
            name="Show",
            value="Allow people to see your voice channel (in channel list)",
            inline=False,
        )
        interface_embed.add_field(
            name="Increase Limit",
            value="Increase the user limit of your voice channel",
            inline=False,
        )
        interface_embed.add_field(
            name="Decrease Limit",
            value="Decrease the user limit of your voice channel (0 - no limit)",
            inline=False,
        )

        interface_message = await interface_channel.send(
            embed=interface_embed, view=Interface(self.client.redis)
        )

        data = {
            "cat": str(category.id),
            "gen_id": str(voice_channel.id),
            "open": [],
            "interface": {
                "channel": str(interface_channel.id),
                "msg_id": str(interface_message.id),
            },
        }

        self.client.redis.update_generator(interaction.guild_id, data)

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Setup**",
            description=f"The category **{category.name}**, voice channel {voice_channel.mention}, and interface channel {interface_channel.mention} have been created.\n Join the voice channel to generate a voice channel.",
        )
        await interaction.followup.send(embed=creation_embed)

        return self.client.incr_counter("voice_generator_create")

    @generator_commands.command()
    @commands.bot_has_permissions(manage_channels=True)
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(self, interaction: discord.Interaction):
        """Removes a voice channel generator"""

        self.client.loop.create_task(interaction.response.defer())

        data = self.client.redis.get_generator(interaction.guild_id)

        try:
            data["interface"] = json.loads(data["interface"])
            channel = self.client.get_channel(int(data["interface"]["channel"]))
            msg = await channel.fetch_message(int(data["interface"]["msg_id"]))
            view = discord.ui.View.from_message(msg)
            view.clear_items()
            await msg.edit(view=view)
        except:
            pass

        self.client.redis.r.delete(f"{interaction.guild_id}:gen")

        embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Removal**",
            description=f"The channel will now no longer act as a voice channel generator",
        )
        await interaction.followup.send(embed=embed)

        return self.client.incr_counter("voice_generator_remove")


async def setup(client: MyClient):
    await client.add_cog(VoiceGen(client))
