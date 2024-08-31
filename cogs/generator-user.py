from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from utils.client import VCRolesClient
from utils.generator import GeneratorUtils
from views.interface import MentionableDropdown


class GenInterface(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.utils = GeneratorUtils(client.db)

    interface_commands = app_commands.Group(
        name="interface", description="Interface commands"
    )

    @interface_commands.command(name="lock")
    async def lock_interface(self, interaction: discord.Interaction):
        """Lock your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.lock(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(
        name="unlock",
    )
    async def unlock_interface(self, interaction: discord.Interaction):
        """Unlock your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.unlock(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(
        name="hide",
    )
    async def hide_interface(self, interaction: discord.Interaction):
        """Hide your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.hide(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(name="show")
    async def unhide_interface(self, interaction: discord.Interaction):
        """Show your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.unhide(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(
        name="increase",
    )
    async def increase_limit_interface(self, interaction: discord.Interaction):
        """Increase your generated voice channel user limit"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.increase_limit(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(name="decrease")
    async def decrease_limit_interface(self, interaction: discord.Interaction):
        """Decrease your generated voice channel user limit"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.decrease_limit(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(name="limit")
    @app_commands.describe(limit="The value to set the member limit to.")
    async def set_limit(
        self, interaction: discord.Interaction, limit: app_commands.Range[int, 0, 100]
    ):
        """Set the user limit for your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.set_limit(interaction.user, limit)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(name="rename")
    @app_commands.describe(name="The new name.")
    async def rename_channel(self, interaction: discord.Interaction, name: str):
        """Rename your generated voice channel"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.rename(interaction.user, name)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(name="claim")
    async def claim_channel(self, interaction: discord.Interaction):
        """Claim a generated channel (if owner has left)"""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        message = await self.utils.claim(interaction.user)
        await interaction.response.send_message(message, ephemeral=True)

    @interface_commands.command(name="invite")
    @app_commands.describe(user="The user to invite.", message="The message to send.")
    async def invite_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        message: Optional[str],
    ):
        if not isinstance(interaction.user, discord.Member) or not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        return_message = await self.utils.permit(interaction.user, [user])
        if (
            not interaction.user.voice
            or not interaction.user.voice.channel
            or not await self.utils.in_voice_channel(interaction.user)
            or return_message == self.utils.owner_failure
        ):
            return await interaction.response.send_message(
                return_message, ephemeral=True
            )

        if not message:
            message = f"{interaction.user.mention} wants you to join them in {interaction.user.voice.channel.mention}"

        try:
            await user.send(message)
        except discord.Forbidden:
            return_message += f"\nCould not DM {user.display_name}"
        except discord.HTTPException:
            return_message += f"\nCould not DM {user.display_name}"

        await interaction.response.send_message(return_message, ephemeral=True)

    @interface_commands.command(name="permit")
    async def permit_mentionable(self, interaction: discord.Interaction):
        """Permits roles/users to join you."""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        if not await self.utils.in_voice_channel(interaction.user):
            return await interaction.response.send_message(
                self.utils.channel_failure, ephemeral=True
            )

        await interaction.response.send_message(
            ephemeral=True,
            view=MentionableView(
                "Permit Roles/Members", "permit", self.utils, timeout=60
            ),
            delete_after=60,
        )

    @interface_commands.command(name="restrict")
    async def restrict_mentionable(self, interaction: discord.Interaction):
        """Restricts roles/users to join you."""
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a guild to use this.", ephemeral=True
            )

        if not await self.utils.in_voice_channel(interaction.user):
            return await interaction.response.send_message(
                self.utils.channel_failure, ephemeral=True
            )

        await interaction.response.send_message(
            ephemeral=True,
            view=MentionableView(
                "Restrict Roles/Members", "restrict", self.utils, timeout=60
            ),
            delete_after=60,
        )


class MentionableView(discord.ui.View):
    def __init__(
        self,
        placeholder: str,
        action: Literal["permit", "restrict"],
        utils: GeneratorUtils,
        *,
        timeout: Optional[int] = 180,
    ):
        super().__init__(timeout=timeout)

        self.add_item(MentionableDropdown(placeholder, action, utils))


async def setup(client: VCRolesClient):
    await client.add_cog(GenInterface(client))
