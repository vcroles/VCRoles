from typing import Any

import discord

from utils.database import DatabaseUtils


class Interface(discord.ui.View):
    """
    View for voice generator interfaces
    """

    def __init__(self, db: DatabaseUtils):
        super().__init__(timeout=None)
        self.db = db

    async def in_voice_channel(self, interaction: discord.Interaction) -> bool:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return False

        data = await self.db.get_generator(interaction.guild.id)

        if (
            not interaction.user.voice
            or not interaction.user.voice.channel
            or not interaction.user.voice.channel.category
        ):
            return False

        if str(interaction.user.voice.channel.category.id) != data.categoryId:
            return False

        if str(interaction.user.voice.channel.id) == data.generatorId:
            return False

        return True

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.red,
        custom_id="voicegen:lock",
    )
    async def lock(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):

        if not await self.in_voice_channel(interaction):
            return await interaction.response.send_message(
                "You must be in a voice channel", ephemeral=True
            )

        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].connect = False
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(connect=False)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

        await interaction.response.send_message("Locked voice channel!", ephemeral=True)

    @discord.ui.button(
        label="Unlock",
        style=discord.ButtonStyle.green,
        custom_id="voicegen:unlock",
    )
    async def unlock(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not await self.in_voice_channel(interaction):
            return await interaction.response.send_message(
                "You must be in a voice channel", ephemeral=True
            )

        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].connect = True
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(connect=True)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

        await interaction.response.send_message(
            "Unlocked voice channel!", ephemeral=True
        )

    @discord.ui.button(
        label="Hide",
        style=discord.ButtonStyle.blurple,
        custom_id="voicegen:hide",
    )
    async def hide(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not await self.in_voice_channel(interaction):
            return await interaction.response.send_message(
                "You must be in a voice channel", ephemeral=True
            )

        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].view_channel = False
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(view_channel=False)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

        await interaction.response.send_message("Hidden voice channel!", ephemeral=True)

    @discord.ui.button(
        label="Show",
        style=discord.ButtonStyle.grey,
        custom_id="voicegen:show",
    )
    async def show(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not await self.in_voice_channel(interaction):
            return await interaction.response.send_message(
                "You must be in a voice channel", ephemeral=True
            )

        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].view_channel = True
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(view_channel=True)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

        await interaction.response.send_message("Shown voice channel!", ephemeral=True)

    @discord.ui.button(
        label="Increase Limit",
        style=discord.ButtonStyle.green,
        custom_id="voicegen:increase_limit",
    )
    async def increase_limit(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not await self.in_voice_channel(interaction):
            return await interaction.response.send_message(
                "You must be in a voice channel", ephemeral=True
            )

        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            return

        if not isinstance(interaction.user.voice.channel, discord.VoiceChannel):
            return

        user_limit = interaction.user.voice.channel.user_limit
        await interaction.user.voice.channel.edit(user_limit=user_limit + 1)

        await interaction.response.send_message(
            f"Increased channel limit to {user_limit + 1}!", ephemeral=True
        )

    @discord.ui.button(
        label="Decrease Limit",
        style=discord.ButtonStyle.red,
        custom_id="voicegen:decrease_limit",
    )
    async def decrease_limit(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not await self.in_voice_channel(interaction):
            return await interaction.response.send_message(
                "You must be in a voice channel", ephemeral=True
            )

        if (
            not isinstance(interaction.user, discord.Member)
            or not interaction.user.voice
            or not interaction.user.voice.channel
        ):
            return

        if not isinstance(interaction.user.voice.channel, discord.VoiceChannel):
            return

        user_limit = interaction.user.voice.channel.user_limit
        if user_limit > 0:
            await interaction.user.voice.channel.edit(user_limit=user_limit - 1)

        await interaction.response.send_message(
            f"Decreased channel limit to {user_limit - 1 if user_limit > 0 else user_limit}!",
            ephemeral=True,
        )
