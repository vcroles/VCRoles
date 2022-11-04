import discord
from prisma.enums import VoiceGeneratorOption
from prisma.models import GeneratedChannel

from .database import DatabaseUtils


class GeneratorUtils:
    """Tools for generated channels. All functions return a string to be sent to user."""

    def __init__(self, db: DatabaseUtils) -> None:
        self.db = db
        self.channel_failure = (
            "You must be in a valid voice channel to use this command."
        )
        self.editable_failure = "You are not allowed to edit this channel."
        self.owner_failure = "You must be the channel owner to edit."

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

    @staticmethod
    def is_owner(user: discord.Member, gen_data: GeneratedChannel) -> bool:
        if (
            gen_data.VoiceGenerator
            and VoiceGeneratorOption.OWNER in gen_data.VoiceGenerator.defaultOptions
        ):
            if str(user.id) == gen_data.ownerId:
                return True
            return False
        return True

    async def lock(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

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

        try:
            await user.voice.channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            return "Bot permission error."

        return "Locked voice channel!"

    async def unlock(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

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

        try:
            await user.voice.channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            return "Bot permission error."

        return "Unlocked voice channel!"

    async def hide(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

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

        try:
            await user.voice.channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            return "Bot permission error."

        return "Hidden voice channel!"

    async def unhide(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

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

        try:
            await user.voice.channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            return "Bot permission error."

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

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

        user_limit = user.voice.channel.user_limit

        try:
            await user.voice.channel.edit(user_limit=user_limit + 1)
        except discord.Forbidden:
            return "Bot permission error."

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

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

        user_limit = user.voice.channel.user_limit
        if user_limit > 0:
            try:
                await user.voice.channel.edit(user_limit=user_limit - 1)
            except discord.Forbidden:
                return "Bot permission error."

        return f"Decreased channel member limit to {user_limit - 1 if user_limit > 0 else user_limit}!"

    async def set_limit(self, user: discord.Member, user_limit: int) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
            or not isinstance(user.voice.channel, discord.VoiceChannel)
        ):
            return self.channel_failure

        if user_limit < 0:
            return "Limit cannot be less than 0"

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

        try:
            await user.voice.channel.edit(user_limit=user_limit)
        except discord.Forbidden:
            return "Bot permission error."

        return f"Set channel member limit to {user_limit}!"

    async def rename(self, user: discord.Member, name: str) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

        try:
            await user.voice.channel.edit(name=name)
        except discord.Forbidden:
            return "Bot permission error."
        except discord.HTTPException:
            return "Unable to complete currently. Try again in a minute."

        return f"Changed the channel name to `{name}`!"

    async def restrict(
        self, user: discord.Member, mentionables: list[discord.Role | discord.Member]
    ) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

        overwrites = user.voice.channel.overwrites

        for mentionable in mentionables:
            try:
                overwrites[mentionable].connect = False
            except KeyError:
                overwrites[mentionable] = discord.PermissionOverwrite(connect=False)

        try:
            await user.voice.channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            return "Bot permission error."

        return f"Restricted: {', '.join([m.mention for m in mentionables])}!"

    async def permit(
        self, user: discord.Member, mentionables: list[discord.Role | discord.Member]
    ) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data:
            return self.channel_failure
        if not gen_data.userEditable:
            return self.editable_failure
        if not self.is_owner(user, gen_data):
            return self.owner_failure

        overwrites = user.voice.channel.overwrites

        for mentionable in mentionables:
            try:
                overwrites[mentionable].connect = True
                overwrites[mentionable].view_channel = True
            except KeyError:
                overwrites[mentionable] = discord.PermissionOverwrite(
                    connect=True, view_channel=True
                )
        try:
            await user.voice.channel.edit(overwrites=overwrites)
        except discord.Forbidden:
            return "Bot permission error."

        return f"Permitted: {', '.join([m.mention for m in mentionables])}!"

    async def claim(self, user: discord.Member) -> str:
        if (
            not user.voice
            or not user.voice.channel
            or not await self.in_voice_channel(user)
        ):
            return self.channel_failure

        gen_data = await self.db.get_generated_channel(user.voice.channel.id)

        if not gen_data or not gen_data.VoiceGenerator:
            return self.channel_failure

        if VoiceGeneratorOption.OWNER not in gen_data.VoiceGenerator.defaultOptions:
            return "Cannot claim unclaimable channel."

        if gen_data.ownerId == str(user.id):
            return "You are already the owner of this channel."

        if any([gen_data.ownerId == str(m.id) for m in user.voice.channel.members]):
            return "Cannot claim channel while owner is in channel."

        await self.db.update_generated_channel(user.voice.channel.id, owner_id=user.id)

        return "Successfully claimed channel."
