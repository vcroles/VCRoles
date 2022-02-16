import json

import discord

from utils import RedisUtils


class Interface(discord.ui.View):
    """
    View for voice generator interfaces
    """

    def __init__(self, redis: RedisUtils):
        super().__init__(timeout=None)
        self.redis = redis

    async def in_voice_channel(self, interaction: discord.Interaction):
        data = self.redis.get_generator(interaction.guild.id)

        try:
            data["interface"] = json.loads(data["interface"])
        except:
            data["interface"] = {"channel": "0", "msg_id": "0"}

        try:
            interaction.user.voice.channel
        except:
            return False

        if not interaction.user.voice.channel:
            return False

        if str(interaction.user.voice.channel.category.id) != data["cat"]:
            return False

        if str(interaction.user.voice.channel.id) == data["gen_id"]:
            return False

        return True

    @discord.ui.button(
        label="Lock",
        style=discord.ButtonStyle.red,
        custom_id="voicegen:lock",
    )
    async def lock(self, button: discord.ui.Button, interaction: discord.Interaction):

        if not await self.in_voice_channel(interaction):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].connect = False
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(connect=False)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

    @discord.ui.button(
        label="Unlock",
        style=discord.ButtonStyle.green,
        custom_id="voicegen:unlock",
    )
    async def unlock(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self.in_voice_channel(interaction):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].connect = True
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(connect=True)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

    @discord.ui.button(
        label="Hide",
        style=discord.ButtonStyle.blurple,
        custom_id="voicegen:hide",
    )
    async def hide(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self.in_voice_channel(interaction):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].view_channel = False
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(view_channel=False)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

    @discord.ui.button(
        label="Show",
        style=discord.ButtonStyle.grey,
        custom_id="voicegen:show",
    )
    async def show(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self.in_voice_channel(interaction):
            return

        overwrites = interaction.user.voice.channel.overwrites
        try:
            overwrites[interaction.user.guild.default_role].view_channel = True
        except KeyError:
            overwrites[
                interaction.user.guild.default_role
            ] = discord.PermissionOverwrite(view_channel=True)
        await interaction.user.voice.channel.edit(overwrites=overwrites)

    @discord.ui.button(
        label="Increase Limit",
        style=discord.ButtonStyle.green,
        custom_id="voicegen:increase_limit",
    )
    async def increase_limit(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if not await self.in_voice_channel(interaction):
            return

        user_limit = interaction.user.voice.channel.user_limit
        await interaction.user.voice.channel.edit(user_limit=user_limit + 1)

    @discord.ui.button(
        label="Decrease Limit",
        style=discord.ButtonStyle.red,
        custom_id="voicegen:decrease_limit",
    )
    async def decrease_limit(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        if not await self.in_voice_channel(interaction):
            return

        user_limit = interaction.user.voice.channel.user_limit
        if user_limit > 0:
            await interaction.user.voice.channel.edit(user_limit=user_limit - 1)
