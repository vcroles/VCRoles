import discord
from utils.database import DatabaseUtils


class GeneratorUtils:
    """Tools for generated channels. All functions return a string to be sent to user."""

    def __init__(self, db: DatabaseUtils) -> None:
        self.db = db

    @property
    def channel_failure(self):
        return "You must be in a voice channel to use this command."

    @property
    def editable_failure(self):
        return "You are not allowed to edit the channel."

    async def in_voice_channel(self, user: discord.Member) -> bool:
        data = await self.db.get_generators(user.guild.id)

        if not user.voice or not user.voice.channel or not user.voice.channel.category:
            return False

        return any(
            [
                str(user.voice.channel.category.id) == d.categoryId
                and str(user.voice.channel.id) != d.generatorId
                for d in data
            ]
        )

    async def lock(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.userEditable:
            return self.editable_failure

        if gen_data.VoiceGenerator and gen_data.VoiceGenerator.defaultRole:
            default_role = user.guild.get_role(int(gen_data.VoiceGenerator.defaultRole))
            if not default_role:
                default_role = user.guild.default_role
        else:
            default_role = user.guild.default_role

        overwrites = user.voice.channel.overwrites

        try:
            overwrites[default_role].connect = False
        except KeyError:
            overwrites[default_role] = discord.PermissionOverwrite(connect=False)

        await user.voice.channel.edit(overwrites=overwrites)

        return "Locked voice channel!"

    async def unlock(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.userEditable:
            return self.editable_failure

        if gen_data.VoiceGenerator and gen_data.VoiceGenerator.defaultRole:
            default_role = user.guild.get_role(int(gen_data.VoiceGenerator.defaultRole))
            if not default_role:
                default_role = user.guild.default_role
        else:
            default_role = user.guild.default_role

        overwrites = user.voice.channel.overwrites

        try:
            overwrites[default_role].connect = True
        except KeyError:
            overwrites[default_role] = discord.PermissionOverwrite(connect=True)

        await user.voice.channel.edit(overwrites=overwrites)

        return "Unlocked voice channel!"

    async def hide(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.userEditable:
            return self.editable_failure

        if gen_data.VoiceGenerator and gen_data.VoiceGenerator.defaultRole:
            default_role = user.guild.get_role(int(gen_data.VoiceGenerator.defaultRole))
            if not default_role:
                default_role = user.guild.default_role
        else:
            default_role = user.guild.default_role

        overwrites = user.voice.channel.overwrites

        try:
            overwrites[default_role].view_channel = False
        except KeyError:
            overwrites[default_role] = discord.PermissionOverwrite(view_channel=False)

        await user.voice.channel.edit(overwrites=overwrites)

        return "Hidden voice channel!"

    async def unhide(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.userEditable:
            return self.editable_failure

        if gen_data.VoiceGenerator and gen_data.VoiceGenerator.defaultRole:
            default_role = user.guild.get_role(int(gen_data.VoiceGenerator.defaultRole))
            if not default_role:
                default_role = user.guild.default_role
        else:
            default_role = user.guild.default_role

        overwrites = user.voice.channel.overwrites

        try:
            overwrites[default_role].view_channel = True
        except KeyError:
            overwrites[default_role] = discord.PermissionOverwrite(view_channel=True)

        await user.voice.channel.edit(overwrites=overwrites)

        return "Made voice channel visible!"

    async def increase_limit(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
            or not isinstance(user.voice.channel, discord.VoiceChannel)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.userEditable:
            return self.editable_failure

        user_limit = user.voice.channel.user_limit
        await user.voice.channel.edit(user_limit=user_limit + 1)

        return f"Increased channel member limit to {user_limit}!"

    async def decrease_limit(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
            or not isinstance(user.voice.channel, discord.VoiceChannel)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.userEditable:
            return self.editable_failure

        user_limit = user.voice.channel.user_limit
        if user_limit > 0:
            await user.voice.channel.edit(user_limit=user_limit - 1)

        return f"Decreased channel member limit to {user_limit - 1 if user_limit > 0 else user_limit}!"
