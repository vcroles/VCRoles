from typing import Any

import discord

from utils.database import DatabaseUtils
from utils.generator import GeneratorUtils


class Interface(discord.ui.View):
    """
    View for voice generator interfaces
    """

    def __init__(self, db: DatabaseUtils):
        super().__init__(timeout=None)
        self.db = db
        self.utils = GeneratorUtils(db)

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.red,
        custom_id="voicegen:lock",
    )
    async def lock(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.lock(interaction.user)

        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="Unlock",
        style=discord.ButtonStyle.green,
        custom_id="voicegen:unlock",
    )
    async def unlock(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.unlock(interaction.user)

        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="Hide",
        style=discord.ButtonStyle.blurple,
        custom_id="voicegen:hide",
    )
    async def hide(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.hide(interaction.user)

        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="Show",
        style=discord.ButtonStyle.grey,
        custom_id="voicegen:show",
    )
    async def show(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.unhide(interaction.user)

        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="Increase Limit",
        style=discord.ButtonStyle.green,
        custom_id="voicegen:increase_limit",
    )
    async def increase_limit(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.increase_limit(interaction.user)

        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(
        label="Decrease Limit",
        style=discord.ButtonStyle.red,
        custom_id="voicegen:decrease_limit",
    )
    async def decrease_limit(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.decrease_limit(interaction.user)

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )

    @discord.ui.button(
        label="Rename", style=discord.ButtonStyle.blurple, custom_id="voicegen:rename"
    )
    async def rename(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ):
        await interaction.response.send_modal(RenameModal(self.db))


class RenameModal(discord.ui.Modal, title="Rename Channel"):
    name: discord.ui.TextInput[Any] = discord.ui.TextInput(label="New Name")

    def __init__(self, db: DatabaseUtils):
        super().__init__()

        self.utils = GeneratorUtils(db)

    async def on_submit(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this."
            )

        message = await self.utils.rename(interaction.user, str(self.name))

        await interaction.response.send_message(
            message,
            ephemeral=True,
        )
