import json

import aiohttp
import discord
import requests
from discord import app_commands
from discord.ext import commands

from bot import MyClient
from checks import check_any, command_available, is_owner


class Advanced(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    async def parse_initial(
        self,
        data: dict[str, dict],
        guild: discord.Guild,
    ):
        for key, value in data.items():
            if key.startswith("!"):
                # Unlink all
                self.client.redis.r.hdel(
                    f"{guild.id}:linked", f"{key.removeprefix('!')}"
                )
            elif key in ["category", "stage", "permanent", "voice"]:
                # Check data
                self.client.loop.create_task(self.parse_channels(value, key, guild))
            elif key == "all":
                # Check data
                self.client.loop.create_task(self.parse_links(value, key, guild))

    async def parse_channels(
        self,
        data: dict,
        key: str,
        guild: discord.Guild,
    ):
        for channel, links in data.items():
            if channel.startswith("!"):
                # Unlink channel
                linked_data = self.client.redis.get_linked(key, guild.id)
                try:
                    linked_data.pop(channel.removeprefix("!"))
                except:
                    pass
                self.client.redis.update_linked(key, guild.id, linked_data)
            else:
                try:
                    int(channel)
                    # channel is id
                except:
                    # channel is name
                    # so get id/make new

                    try:
                        channels = await guild.fetch_channels()
                        if key == "category":
                            done = False
                            for ch in channels:
                                if isinstance(ch, discord.CategoryChannel):
                                    if ch.name == channel:
                                        done = True
                                        break
                            if not done:
                                ch = await guild.create_category_channel(
                                    name=channel, reason="Auto-created by advanced link"
                                )
                        elif key == "stage":
                            done = False
                            for ch in channels:
                                if isinstance(ch, discord.StageChannel):
                                    if ch.name == channel:
                                        done = True
                                        break
                            if not done:
                                ch = await guild.create_stage_channel(
                                    name=channel, reason="Auto-created by advanced link"
                                )
                        elif key == "permanent" or key == "voice":
                            done = False
                            for ch in channels:
                                if isinstance(ch, discord.VoiceChannel):
                                    if ch.name == channel:
                                        done = True
                                        break
                            if not done:
                                ch = await guild.create_voice_channel(
                                    name=channel, reason="Auto-created by advanced link"
                                )
                        channel = str(ch.id)
                    except:
                        continue
                # Check data
                linked_data = self.client.redis.get_linked(key, guild.id)
                if channel not in linked_data:
                    linked_data[channel] = {
                        "roles": [],
                        "suffix": "",
                        "reverse_roles": [],
                    }
                self.client.redis.update_linked(key, guild.id, linked_data)

                self.client.loop.create_task(
                    self.parse_links(links, key, guild, channel)
                )

    async def parse_links(
        self,
        data: dict,
        key: str,
        guild: discord.Guild,
        channel_id: str = None,
    ):
        def get_data_to_edit(linked_data: dict, channel_id: str):
            if channel_id:
                return linked_data[channel_id]
            else:
                return linked_data

        def combine_edit_data(
            linked_data: dict, linked_data_edit: dict, channel_id: str
        ):
            if channel_id:
                linked_data[channel_id] = linked_data_edit
            else:
                linked_data = linked_data_edit
            return linked_data

        # Check data
        for linktype, value in data.items():
            assert isinstance(linktype, str)
            if linktype.startswith("!") and linktype.endswith(
                ("roles", "reverse_roles", "suffix")
            ):
                # Unlink all in linktype
                linked_data = self.client.redis.get_linked(key, guild.id)
                linked_data_edit = get_data_to_edit(linked_data, channel_id)

                if linktype.endswith(("roles", "reverse_roles")):
                    linked_data_edit[linktype] = []
                else:
                    linked_data_edit[linktype] = ""

                linked_data = combine_edit_data(
                    linked_data, linked_data_edit, channel_id
                )
                self.client.redis.update_linked(key, guild.id, linked_data)
            elif linktype in ["roles", "reverse_roles", "suffix"]:
                linked_data = self.client.redis.get_linked(key, guild.id)
                linked_data_edit = get_data_to_edit(linked_data, channel_id)

                if linktype == "roles" or linktype == "reverse_roles":
                    for role in value:
                        if role.startswith("!"):
                            # Unlink role
                            try:
                                # role is id
                                int(role.removeprefix("!"))
                            except:
                                # role is name
                                # so get id/make new
                                done = False
                                for r in guild.roles:
                                    if r.name == role.removeprefix("!"):
                                        done = True
                                        break
                                # make new role
                                if not done:
                                    r = await guild.create_role(
                                        name=role,
                                        reason="Auto-created by advanced link",
                                    )
                                role = str(r.id)
                            if role in linked_data_edit[linktype]:
                                linked_data_edit[linktype].remove(role)
                        else:
                            # Link role
                            try:
                                # role is id
                                int(role)
                            except:
                                # role is name
                                # so get id/make new
                                done = False
                                for r in guild.roles:
                                    if r.name == role:
                                        done = True
                                        break
                                # make new channel
                                if not done:
                                    r = await guild.create_role(
                                        name=role,
                                        reason="Auto-created by advanced link",
                                    )
                                role = str(r.id)

                            if role not in linked_data_edit[linktype]:
                                linked_data_edit[linktype].append(role)
                elif linktype == "suffix":
                    linked_data_edit[linktype] = value
                linked_data = combine_edit_data(
                    linked_data, linked_data_edit, channel_id
                )
                self.client.redis.update_linked(key, guild.id, linked_data)

    @app_commands.command()
    @app_commands.describe(attachment="Select a JSON file to use")
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def advanced(
        self,
        interaction: discord.Interaction,
        attachment: discord.Attachment,
    ):
        """
        Command for advanced users. Allows you to add/remove/edit a large number of links at once.
        """
        await interaction.response.defer()
        if not interaction.guild:
            return await interaction.followup.send(
                "This command can only be used in a server."
            )
        if not attachment.content_type.startswith("application/json"):
            return await interaction.followup.send("Incorrect JSON format")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    data = await response.json()
        except json.decoder.JSONDecodeError:
            return await interaction.followup.send("Incorrect JSON format")
        except requests.JSONDecodeError:
            return await interaction.followup.send("Incorrect JSON format")
        except:
            return await interaction.followup.send("Unknown error")

        if not isinstance(data, dict):
            return await interaction.followup.send("Incorrect JSON format")

        guild = await self.client.fetch_guild(interaction.guild_id)

        await self.parse_initial(data, guild)

        await interaction.followup.send("Done")

        return self.client.incr_counter("advanced")

    @app_commands.command()
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    async def export(self, interaction: discord.Interaction):
        """
        Command for advanced users. Allows you to export all links to a file.
        """
        await interaction.response.defer()
        if not interaction.guild:
            return await interaction.followup.send(
                "This command can only be used in a server."
            )

        data = {}
        for type in ["all", "category", "permanent", "stage", "voice"]:
            data[type] = self.client.redis.get_linked(type, interaction.guild_id)

        with open(f"exports/{interaction.guild_id}.json", "w") as f:
            json.dump(data, f, indent=4)

        with open(f"exports/{interaction.guild_id}.json", "rb") as f:
            file = discord.File(f, "data.json")

        await interaction.followup.send("Here is the exported data.", file=file)

        return self.client.incr_counter("export")


async def setup(client: MyClient):
    await client.add_cog(Advanced(client))
