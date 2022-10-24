import discord
from discord import app_commands
from discord.ext import commands
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
                if category and isinstance(category, discord.guild.GuildChannel):
                    await category.delete()
            except:
                pass

        if data.generatorId:
            try:
                generator_channel = await self.client.fetch_channel(
                    int(data.generatorId)
                )
                if generator_channel and isinstance(
                    generator_channel, discord.guild.GuildChannel
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
                    interface_channel, discord.guild.GuildChannel
                ):
                    await interface_channel.delete()
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
        category_name: str = "Voice Generator",
        voice_channel_name: str = "Voice Generator",
        interface_channel_name: str = "VC Roles Interface",
    ):
        """Creates a voice channel generator"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        await interaction.response.defer()

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
                "Failed to create generator channels. Please check permissions and try again."
            )
            return

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
        ]

        for field in embed_fields:
            interface_embed.add_field(name=field[0], value=field[1], inline=False)

        interface_message = await interface_channel.send(
            embed=interface_embed, view=Interface(self.client.db)
        )

        await self.client.db.update_generator(
            interaction.guild.id,
            voice_channel.id,
            category_id=str(category.id),
            interface_channel=str(interface_channel.id),
            interface_message=str(interface_message.id),
        )

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


async def setup(client: VCRolesClient):
    await client.add_cog(VoiceGen(client))
