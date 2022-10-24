import discord
from discord import app_commands
from discord.ext import commands
from prisma.models import VoiceGenerator

from utils.client import VCRolesClient


class GenInterface(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client

    interface_commands = app_commands.Group(
        name="interface", description="Interface commands"
    )

    async def in_voice_channel(
        self, data: list[VoiceGenerator], user: discord.Member
    ) -> bool:
        if not user.voice or not user.voice.channel or not user.voice.channel.category:
            return False

        return any(
            [
                str(user.voice.channel.category.id) == d.categoryId
                and str(user.voice.channel.id) != d.generatorId
                for d in data
            ]
        )

    async def lock(self, user: discord.Member):
        if not user.voice or not user.voice.channel:
            return

        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].connect = False
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                connect=False
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def unlock(self, user: discord.Member):
        if not user.voice or not user.voice.channel:
            return

        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].connect = True
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                connect=True
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def hide(self, user: discord.Member):
        if not user.voice or not user.voice.channel:
            return

        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].view_channel = False
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                view_channel=False
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def unhide(self, user: discord.Member):
        if not user.voice or not user.voice.channel:
            return

        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].view_channel = True
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                view_channel=True
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def increase_limit(self, user: discord.Member):
        if not user.voice or not user.voice.channel:
            return
        if not isinstance(user.voice.channel, discord.VoiceChannel):
            return

        user_limit = user.voice.channel.user_limit
        await user.voice.channel.edit(user_limit=user_limit + 1)

    async def decrease_limit(self, user: discord.Member):
        if not user.voice or not user.voice.channel:
            return
        if not isinstance(user.voice.channel, discord.VoiceChannel):
            return

        user_limit = user.voice.channel.user_limit
        if user_limit > 0:
            await user.voice.channel.edit(user_limit=user_limit - 1)

    @interface_commands.command(name="lock")
    async def lock_interface(self, interaction: discord.Interaction):
        """Lock your generated voice channel"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        data = await self.client.db.get_generators(interaction.guild.id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            return await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.lock(interaction.user)
        await interaction.response.send_message("Generator locked.", ephemeral=True)

        return self.client.incr_counter("interface_lock")

    @interface_commands.command(
        name="unlock",
    )
    async def unlock_interface(self, interaction: discord.Interaction):
        """Unlock your generated voice channel"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        data = await self.client.db.get_generators(interaction.guild.id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            return await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.unlock(interaction.user)
        await interaction.response.send_message("Generator unlocked.", ephemeral=True)

        return self.client.incr_counter("interface_unlock")

    @interface_commands.command(
        name="hide",
    )
    async def hide_interface(self, interaction: discord.Interaction):
        """Hide your generated voice channel"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        data = await self.client.db.get_generators(interaction.guild.id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            return await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.hide(interaction.user)
        await interaction.response.send_message("Generator hidden.", ephemeral=True)

        return self.client.incr_counter("interface_hide")

    @interface_commands.command(name="show")
    async def unhide_interface(self, interaction: discord.Interaction):
        """Show your generated voice channel"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        data = await self.client.db.get_generators(interaction.guild.id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            return await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.unhide(interaction.user)
        await interaction.response.send_message("Generator unhidden.", ephemeral=True)

        return self.client.incr_counter("interface_unhide")

    @interface_commands.command(
        name="increase",
    )
    async def increase_limit_interface(self, interaction: discord.Interaction):
        """Increase your generated voice channel user limit"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        data = await self.client.db.get_generators(interaction.guild.id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            return await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.increase_limit(interaction.user)
        await interaction.response.send_message(
            "Generator limit increased.", ephemeral=True
        )

        return self.client.incr_counter("interface_increase")

    @interface_commands.command(name="decrease")
    async def decrease_limit_interface(self, interaction: discord.Interaction):
        """Decrease your generated voice channel user limit"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        data = await self.client.db.get_generators(interaction.guild.id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            return await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.decrease_limit(interaction.user)
        await interaction.response.send_message(
            "Generator limit decreased.", ephemeral=True
        )

        return self.client.incr_counter("interface_decrease")


async def setup(client: VCRolesClient):
    await client.add_cog(GenInterface(client))
