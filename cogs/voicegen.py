from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner
from views.interface import Interface


class VoiceGen(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    async def remove_generator(self, data: dict[str, Union[str, list]]):
        if "cat" in data and data["cat"] != "":
            try:
                cat = await self.client.fetch_channel(int(data["cat"]))
                if cat:
                    await cat.delete()
            except:
                pass
        if "gen_id" in data and data["gen_id"] != "":
            try:
                gen = await self.client.fetch_channel(int(data["gen_id"]))
                if gen:
                    await gen.delete()
            except:
                pass
        if (
            "interface" in data
            and "channel" in data["interface"]
            and data["interface"]["channel"] != ""
        ):
            try:
                interface = await self.client.fetch_channel(
                    int(data["interface"]["channel"])
                )
                if interface:
                    try:
                        await interface.delete()
                    except:
                        try:
                            msg = await interface.fetch_message(
                                int(data["interface"]["msg_id"])
                            )
                            await msg.delete()
                        except:
                            pass
            except:
                pass

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

        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )
        await interaction.response.defer()

        data = self.client.redis.get_generator(interaction.guild_id)

        if any([data["cat"], data["gen_id"], data["interface"]["channel"]]):
            self.client.loop.create_task(self.remove_generator(data))

        try:
            overwrites = {
                interaction.guild.me: discord.PermissionOverwrite(manage_channels=True)
            }
            category = await interaction.guild.create_category(
                name=category_name, overwrites=overwrites
            )
            voice_channel = await category.create_voice_channel(name=voice_channel_name)

            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False
                ),
                interaction.guild.me: discord.PermissionOverwrite(send_messages=True),
            }

            interface_channel = await category.create_text_channel(
                name=interface_channel_name, overwrites=overwrites
            )
        except:
            await interaction.followup.send(
                "Failed to create generator channels. Please check permissions or try again later."
            )
            return

        interface_embed = discord.Embed(
            title="Voice Generator Interface",
            description=f"You can use this interface to customize your private voice channel.",
            color=discord.Color.blue(),
        )
        interface_embed.set_thumbnail(url=self.client.user.avatar.url)
        interface_embed.set_footer(text="Use these commands via the buttons below.")

        embed_fields = [
            ["Lock", "Stop people from joining your voice channel"],
            ["Unlock", "Allow people to join your voice channel"],
            ["Hide", "Stop people from seeing your voice channel (in channel list)"],
            ["Show", "Allow people to see your voice channel (in channel list)"],
            ["Increase Limit", "Increase the user limit of your voice channel"],
            [
                "Decrease Limit",
                "Decrease the user limit of your voice channel (0 - no limit)",
            ],
        ]

        for field in embed_fields:
            interface_embed.add_field(name=field[0], value=field[1], inline=False)

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

        self.client.loop.create_task(self.remove_generator(data))

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
