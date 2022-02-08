import json
import discord
from discord.ext import commands
from bot import MyClient


class GenInterface(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.client.user.id:
            return

        data = self.client.redis.get_generator(payload.guild_id)

        try:
            data["interface"] = json.loads(data["interface"])
        except:
            data["interface"] = {"channel": "0", "msg_id": "0"}

        if data["interface"]["msg_id"] != str(payload.message_id):
            return

        if payload.emoji.name not in ["🔒", "🔓", "🚫", "👁", "➕", "➖"]:
            return

        guild = self.client.get_guild(payload.guild_id)
        user = await guild.fetch_member(payload.user_id)

        if not user.voice.channel:
            channel = self.client.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, user)
            return

        if str(user.voice.channel.category.id) != data["cat"]:
            channel = self.client.get_channel(payload.channel_id)
            msg = await channel.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, user)
            return

        if payload.emoji.name == "🔒":
            await self.lock(user)
        elif payload.emoji.name == "🔓":
            await self.unlock(user)
        elif payload.emoji.name == "🚫":
            await self.hide(user)
        elif payload.emoji.name == "👁":
            await self.unhide(user)
        elif payload.emoji.name == "➕":
            await self.increase_limit(user)
        elif payload.emoji.name == "➖":
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


def setup(client: MyClient):
    client.add_cog(GenInterface(client))
