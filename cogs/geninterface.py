import json

import discord
from discord import app_commands
from discord.ext import commands

from bot import MyClient


class GenInterface(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    interface_commands = app_commands.Group(
        name="interface", description="Interface commands"
    )

    async def in_voice_channel(self, data, user: discord.Member):

        try:
            user.voice
            user.voice.channel
        except AttributeError:
            return False

        if not user.voice.channel:
            return False

        if str(user.voice.channel.category.id) != data["cat"]:
            return False

        if str(user.voice.channel.id) == data["gen_id"]:
            return False

        return True

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.client.user.id:
            return

        if payload.emoji.name not in ["🔒", "🔓", "🚫", "👁", "⬆", "⬇"]:
            return

        data = self.client.redis.get_generator(payload.guild_id)

        try:
            data["interface"] = json.loads(data["interface"])
        except:
            data["interface"] = {"channel": "0", "msg_id": "0"}

        if data["interface"]["msg_id"] != str(payload.message_id):
            return

        guild = self.client.get_guild(payload.guild_id)
        user = await guild.fetch_member(payload.user_id)

        in_voice = await self.in_voice_channel(data, user)

        if not in_voice:
            try:
                channel = self.client.get_channel(payload.channel_id)
                msg = await channel.fetch_message(payload.message_id)
                await msg.remove_reaction(payload.emoji, user)
            except:
                pass
            finally:
                return

        if payload.emoji.name == "🔒":
            await self.lock(user)
        elif payload.emoji.name == "🔓":
            await self.unlock(user)
        elif payload.emoji.name == "🚫":
            await self.hide(user)
        elif payload.emoji.name == "👁":
            await self.unhide(user)
        elif payload.emoji.name == "⬆":
            await self.increase_limit(user)
        elif payload.emoji.name == "⬇":
            await self.decrease_limit(user)

        channel = self.client.get_channel(payload.channel_id)
        msg = await channel.fetch_message(payload.message_id)
        await msg.remove_reaction(payload.emoji, user)

    async def lock(self, user: discord.Member):
        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].connect = False
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                connect=False
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def unlock(self, user: discord.Member):
        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].connect = True
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                connect=True
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def hide(self, user: discord.Member):
        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].view_channel = False
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                view_channel=False
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def unhide(self, user: discord.Member):
        overwrites = user.voice.channel.overwrites
        try:
            overwrites[user.guild.default_role].view_channel = True
        except KeyError:
            overwrites[user.guild.default_role] = discord.PermissionOverwrite(
                view_channel=True
            )
        await user.voice.channel.edit(overwrites=overwrites)

    async def increase_limit(self, user: discord.Member):
        user_limit = user.voice.channel.user_limit
        await user.voice.channel.edit(user_limit=user_limit + 1)

    async def decrease_limit(self, user: discord.Member):
        user_limit = user.voice.channel.user_limit
        if user_limit > 0:
            await user.voice.channel.edit(user_limit=user_limit - 1)

    @interface_commands.command(name="lock")
    async def lock_interface(self, interaction: discord.Interaction):
        """Lock your generated voice channel"""
        data = self.client.redis.get_generator(interaction.guild_id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            await interaction.response.send_message(
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
        data = self.client.redis.get_generator(interaction.guild_id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            await interaction.response.send_message(
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
        data = self.client.redis.get_generator(interaction.guild_id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.hide(interaction.user)
        await interaction.response.send_message("Generator hidden.", ephemeral=True)

        return self.client.incr_counter("interface_hide")

    @interface_commands.command(name="show")
    async def unhide_interface(self, interaction: discord.Interaction):
        """Show your generated voice channel"""
        data = self.client.redis.get_generator(interaction.guild_id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            await interaction.response.send_message(
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
        data = self.client.redis.get_generator(interaction.guild_id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            await interaction.response.send_message(
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
        data = self.client.redis.get_generator(interaction.guild_id)

        in_vc = await self.in_voice_channel(data, interaction.user)
        if not in_vc:
            await interaction.response.send_message(
                "You must be in a generator voice channel to use this command.",
                ephemeral=True,
            )

        await self.decrease_limit(interaction.user)
        await interaction.response.send_message(
            "Generator limit decreased.", ephemeral=True
        )

        return self.client.incr_counter("interface_decrease")


async def setup(client: MyClient):
    await client.add_cog(GenInterface(client))
