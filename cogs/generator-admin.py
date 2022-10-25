from typing import Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands
from prisma.enums import VoiceGeneratorOption, VoiceGeneratorType
from prisma.models import VoiceGenerator

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from views.interface import Interface


class VoiceGen(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    async def remove_generator(self, data: VoiceGenerator) -> None:
        if data.categoryId:
            try:
                category = await self.client.fetch_channel(int(data.categoryId))
                if category and isinstance(category, discord.CategoryChannel):
                    await category.delete()
            except:
                pass

        if data.generatorId:
            try:
                generator_channel = await self.client.fetch_channel(
                    int(data.generatorId)
                )
                if generator_channel and isinstance(
                    generator_channel, discord.VoiceChannel
                ):
                    await generator_channel.delete()
            except:
                pass

        if data.interfaceChannel:
            try:
                interface_channel = await self.client.fetch_channel(
                    int(data.interfaceChannel)
                )
                if interface_channel and isinstance(
                    interface_channel, discord.TextChannel
                ):
                    await interface_channel.delete()
            except:
                pass

    def get_interface_embed(self) -> discord.Embed:
        interface_embed = discord.Embed(
            title="Voice Generator Interface",
            description=f"You can use this interface to customize your private voice channel.",
            color=discord.Color.blue(),
        )
        interface_embed.set_thumbnail(
            url=self.client.user.avatar.url
            if self.client.user and self.client.user.avatar
            else None
        )
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
            ["Rename", "Rename your voice channel"],
        ]

        for field in embed_fields:
            interface_embed.add_field(name=field[0], value=field[1], inline=False)

        return interface_embed

    async def create_channels(
        self,
        interaction: discord.Interaction,
        category_name: str,
        voice_channel_name: str,
        create_interface_channel: bool,
        interface_channel_name: str,
    ) -> Optional[
        Tuple[
            discord.CategoryChannel,
            discord.VoiceChannel,
            Optional[discord.TextChannel],
            Optional[discord.Message],
        ]
    ]:
        assert interaction.guild
        try:
            category = await interaction.guild.create_category(
                name=category_name,
                overwrites={
                    interaction.guild.me: discord.PermissionOverwrite(
                        manage_channels=True
                    )
                },
            )

            voice_channel = await category.create_voice_channel(name=voice_channel_name)

            if create_interface_channel:
                overwrites = {
                    interaction.guild.default_role: discord.PermissionOverwrite(
                        send_messages=False
                    ),
                    interaction.guild.me: discord.PermissionOverwrite(
                        send_messages=True
                    ),
                }

                interface_channel = await category.create_text_channel(
                    name=interface_channel_name, overwrites=overwrites
                )

                interface_message = await interface_channel.send(
                    embed=self.get_interface_embed(), view=Interface(self.client.db)
                )
            else:
                interface_channel = None
                interface_message = None
        except:
            return await interaction.followup.send(
                "Failed to create generator channels. Please check permissions and try again."
            )
        return (category, voice_channel, interface_channel, interface_message)

    generator_commands = app_commands.Group(
        name="generator", description="Generator channel commands"
    )

    create_commands = app_commands.Group(
        name="create",
        description="Commands to create voice generators.",
        parent=generator_commands,
    )

    @create_commands.command()
    @app_commands.describe(
        category_name="Name of generator category",
        voice_channel_name="Name of voice channel",
        interface_channel_name="Name of interface channel",
        user_editable="Whether users can edit their generated channel",
        channel_limit="The maximum of generated channels allowed",
        create_interface_channel="Whether to create an interface channel",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def default(
        self,
        interaction: discord.Interaction,
        user_editable: bool,
        channel_limit: int = 100,
        category_name: str = "Voice Generator",
        voice_channel_name: str = "Voice Generator",
        create_interface_channel: bool = True,
        interface_channel_name: str = "VC Roles Interface",
    ):
        """Creates a voice channel generator"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        if not user_editable:
            create_interface_channel = False

        await interaction.response.defer()
        data = await self.create_channels(
            interaction,
            category_name,
            voice_channel_name,
            create_interface_channel,
            interface_channel_name,
        )
        if not data:
            return
        category = data[0]
        voice_channel = data[1]
        interface_channel = data[2]
        interface_message = data[3]

        await self.client.db.update_generator(
            interaction.guild.id,
            voice_channel.id,
            category_id=str(category.id),
            interface_channel=str(interface_channel.id) if interface_channel else None,
            interface_message=str(interface_message.id) if interface_message else None,
            gen_type=VoiceGeneratorType.DEFAULT,
            default_options=[VoiceGeneratorOption.EDITABLE, VoiceGeneratorOption.OWNER]
            if user_editable
            else [VoiceGeneratorOption.OWNER],
            channel_limit=channel_limit,
        )

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Setup - Default**",
            description=f"The category **{category.name}**, voice channel {voice_channel.mention}{f', and interface channel {interface_channel.mention}' if interface_channel else ''} have been created.\n Join the voice channel to generate a voice channel.",
        )
        await interaction.followup.send(embed=creation_embed)

        return self.client.incr_counter("voice_generator_create")

    @create_commands.command()
    @app_commands.describe(
        category_name="Name of generator category",
        generated_channel_name="Name of generated voice channel",
        interface_channel_name="Name of interface channel",
        user_editable="Whether users can edit their generated channel",
        channel_limit="The maximum of generated channels allowed",
        create_interface_channel="Whether to create an interface channel",
        voice_channel_name="Name of joinable channel",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def numbered(
        self,
        interaction: discord.Interaction,
        user_editable: bool,
        generated_channel_name: str,
        channel_limit: int,
        category_name: str = "Voice Generator",
        create_interface_channel: bool = True,
        interface_channel_name: str = "VC Roles Interface",
        voice_channel_name: str = "Voice Generator",
    ):
        """Creates a numbered voice channel generator"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        if not user_editable:
            create_interface_channel = False

        await interaction.response.defer()
        data = await self.create_channels(
            interaction,
            category_name,
            voice_channel_name,
            create_interface_channel,
            interface_channel_name,
        )
        if not data:
            return
        category = data[0]
        voice_channel = data[1]
        interface_channel = data[2]
        interface_message = data[3]

        await self.client.db.update_generator(
            interaction.guild.id,
            voice_channel.id,
            category_id=str(category.id),
            interface_channel=str(interface_channel.id) if interface_channel else None,
            interface_message=str(interface_message.id) if interface_message else None,
            gen_type=VoiceGeneratorType.NUMBERED,
            default_options=[VoiceGeneratorOption.EDITABLE, VoiceGeneratorOption.OWNER]
            if user_editable
            else [VoiceGeneratorOption.OWNER],
            channel_limit=channel_limit,
            channel_name=generated_channel_name,
        )

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Setup - Numbered**",
            description=f"The category **{category.name}**, voice channel {voice_channel.mention}{f', and interface channel {interface_channel.mention}' if interface_channel else ''} have been created.\n Join the voice channel to generate a voice channel.",
        )
        await interaction.followup.send(embed=creation_embed)

        return self.client.incr_counter("voice_generator_create")

    @create_commands.command()
    @app_commands.describe(
        category_name="Name of generator category",
        voice_channel_name="Name of voice channel",
        interface_channel_name="Name of interface channel",
        user_editable="Whether users can edit their generated channel",
        channel_limit="The maximum of generated channels allowed",
        create_interface_channel="Whether to create an interface channel",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def clone(
        self,
        interaction: discord.Interaction,
        user_editable: bool,
        voice_channel_name: str,
        channel_limit: int = 100,
        category_name: str = "Voice Generator",
        create_interface_channel: bool = True,
        interface_channel_name: str = "VC Roles Interface",
    ):
        """Creates a voice channel generator which clones a channel"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        if not user_editable:
            create_interface_channel = False

        await interaction.response.defer()
        data = await self.create_channels(
            interaction,
            category_name,
            voice_channel_name,
            create_interface_channel,
            interface_channel_name,
        )
        if not data:
            return
        category = data[0]
        voice_channel = data[1]
        interface_channel = data[2]
        interface_message = data[3]

        await self.client.db.update_generator(
            interaction.guild.id,
            voice_channel.id,
            category_id=str(category.id),
            interface_channel=str(interface_channel.id) if interface_channel else None,
            interface_message=str(interface_message.id) if interface_message else None,
            gen_type=VoiceGeneratorType.CLONED,
            default_options=[VoiceGeneratorOption.EDITABLE, VoiceGeneratorOption.OWNER]
            if user_editable
            else [VoiceGeneratorOption.OWNER],
            channel_limit=channel_limit,
        )

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Setup - Cloned**",
            description=f"The category **{category.name}**, voice channel {voice_channel.mention}{f', and interface channel {interface_channel.mention}' if interface_channel else ''} have been created.\n Join the voice channel to generate a voice channel.",
        )
        await interaction.followup.send(embed=creation_embed)

        return self.client.incr_counter("voice_generator_create")

    @create_commands.command()
    @app_commands.describe(
        category_name="Name of generator category",
        generated_channel_name="Name of voice channel variables: $username, $count",
        interface_channel_name="Name of interface channel",
        user_editable="Whether users can edit their generated channel",
        channel_limit="The maximum of generated channels allowed",
        create_interface_channel="Whether to create an interface channel",
        voice_channel_name="The name of the generating channel",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.bot_has_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def custom_name(
        self,
        interaction: discord.Interaction,
        user_editable: bool,
        generated_channel_name: str,
        channel_limit: int,
        category_name: str = "Voice Generator",
        create_interface_channel: bool = True,
        interface_channel_name: str = "VC Roles Interface",
        voice_channel_name: str = "Voice Generator",
    ):
        """Creates a voice channel generator with custom name"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        if not user_editable:
            create_interface_channel = False

        await interaction.response.defer()
        data = await self.create_channels(
            interaction,
            category_name,
            voice_channel_name,
            create_interface_channel,
            interface_channel_name,
        )
        if not data:
            return
        category = data[0]
        voice_channel = data[1]
        interface_channel = data[2]
        interface_message = data[3]

        await self.client.db.update_generator(
            interaction.guild.id,
            voice_channel.id,
            category_id=str(category.id),
            interface_channel=str(interface_channel.id) if interface_channel else None,
            interface_message=str(interface_message.id) if interface_message else None,
            gen_type=VoiceGeneratorType.CUSTOM_NAME,
            default_options=[VoiceGeneratorOption.EDITABLE, VoiceGeneratorOption.OWNER]
            if user_editable
            else [VoiceGeneratorOption.OWNER],
            channel_limit=channel_limit,
            channel_name=generated_channel_name,
        )

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Numbered Voice Generator Setup**",
            description=f"The category **{category.name}**, voice channel {voice_channel.mention}{f', and interface channel {interface_channel.mention}' if interface_channel else ''} have been created.\n Join the voice channel to generate a voice channel.",
        )
        await interaction.followup.send(embed=creation_embed)

        return self.client.incr_counter("voice_generator_create")

    @generator_commands.command()
    @app_commands.describe(generator="The generator channel to edit.")
    @commands.bot_has_permissions(manage_channels=True)
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove(
        self, interaction: discord.Interaction, generator: discord.VoiceChannel
    ):
        """Removes a voice channel generator"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        await interaction.response.defer()

        gen_data = await self.client.db.get_generator(
            interaction.guild.id, generator.id
        )

        if not gen_data:
            return await interaction.followup.send(
                "Please select a valid generator channel"
            )

        await self.remove_generator(gen_data)

        await self.client.db.delete_generator(interaction.guild.id, generator.id)

        embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Removal**",
            description=f"The channel will now no longer act as a voice channel generator",
        )
        await interaction.followup.send(embed=embed)

        return self.client.incr_counter("voice_generator_remove")

    @generator_commands.command()
    @app_commands.describe(
        generator="The generator channel to edit.",
        option="The option to enable/disable.",
        state="The state to set the option to.",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle(
        self,
        interaction: discord.Interaction,
        generator: discord.VoiceChannel,
        option: VoiceGeneratorOption,
        state: bool,
    ):
        """Toggles a default option for a voice generator."""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        gen_data = await self.client.db.get_generator(
            interaction.guild.id, generator.id
        )

        if not gen_data:
            return await interaction.response.send_message(
                "Please select a valid generator channel"
            )

        if state is True and option not in gen_data.defaultOptions:
            gen_data.defaultOptions.append(option)
        elif state is False and option in gen_data.defaultOptions:
            gen_data.defaultOptions.remove(option)
        else:
            return await interaction.response.send_message(
                f"{option} is already set to {state} for {generator.mention}."
            )

        await self.client.db.update_generator(
            interaction.guild.id,
            generator.id,
            generator.category.id if generator.category else "",
            default_options=gen_data.defaultOptions,
        )

        await interaction.response.send_message(
            f"Set {option} to {state} in {generator.mention}"
        )

    @generator_commands.command()
    @app_commands.describe(
        generator="The generator channel to edit.",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def options(
        self,
        interaction: discord.Interaction,
        generator: discord.VoiceChannel,
    ):
        """Lists the default options set for a generator channel."""

        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        gen_data = await self.client.db.get_generator(
            interaction.guild.id, generator.id
        )

        if not gen_data:
            return await interaction.response.send_message(
                "Please select a valid generator channel"
            )

        if gen_data.defaultOptions:
            await interaction.response.send_message(
                f"The currently enabled for {generator.mention} options are: {', '.join([option for option in gen_data.defaultOptions])}"
            )
        else:
            await interaction.response.send_message(
                f"There are no default enabled options for {generator.mention}"
            )

    @generator_commands.command(name="role")
    @app_commands.describe(
        default_role="The default role the bot edits permissions for",
        generator="The generator channel to edit.",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def set_role(
        self,
        interaction: discord.Interaction,
        generator: discord.VoiceChannel,
        default_role: discord.Role,
    ):
        """Sets the default role the bot edits permissions for"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        gen_data = await self.client.db.get_generator(
            interaction.guild.id, generator.id
        )

        if not gen_data:
            return await interaction.response.send_message(
                "Please select a valid generator channel"
            )

        await self.client.db.update_generator(
            interaction.guild.id,
            generator.id,
            generator.category.id if generator.category else "",
            default_role_id=str(default_role.id),
        )

        await interaction.response.send_message(
            f"Set the default permission role for {generator.mention} to `@{default_role.name}`"
        )


async def setup(client: VCRolesClient):
    await client.add_cog(VoiceGen(client))
