import asyncio
import os
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTS
from mutagen.mp3 import MP3

from bot import MyClient

tts_langs = Literal[
    "af: Afrikaans",
    "ar: Arabic",
    "bn: Bengali",
    "ca: Catalan",
    "cs: Czech",
    "da: Danish",
    "de: German",
    "en: English",
    "es: Spanish",
    "fr: French",
    "hi: Hindi",
    "it: Italian",
    "ja: Japanese",
    "ko: Korean",
    "my: Myanmar (Burmese)",
    "nl: Dutch",
    "no: Norwegian",
    "pl: Polish",
    "pt: Portuguese",
    "ru: Russian",
    "sv: Swedish",
    "th: Thai",
    "tr: Turkish",
    "zh-CN: Chinese",
    "zh: Chinese (Mandarin)",
]


class TTS(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    tts_commands = app_commands.Group(name="tts", description="Text To Speech commands")

    @tts_commands.command()
    @app_commands.describe(
        message="Enter the message you want to read",
        language="Enter the language you want to use (Default: English `en: English`)",
        leave="The bot leaves the voice channel after reading the message (Default: True)",
    )
    async def play(
        self,
        interaction: discord.Interaction,
        message: str,
        language: Optional[tts_langs] = "en: English",
        leave: Optional[bool] = True,
    ):
        """Used to make the bot read a message in a voice channel"""
        index = language.find(":")
        language_code = language[0:index]

        data = self.client.redis.get_guild_data(interaction.guild_id)

        if data["tts:enabled"] == "False":
            return await interaction.response.send_message(
                f"TTS isn't enabled in this server."
            )
        if len(message) > 250:
            return await interaction.response.send_message(
                f"The message is over the 250 character limit"
            )
        if data["tts:enabled"] == "True":

            try:
                role = interaction.guild.get_role(int(data["tts:role"]))
            except:
                role = None

            if role in interaction.user.roles or data["tts:role"] == "None":
                if interaction.user.voice.channel:
                    tts_message = gTTS(text=message, lang=language_code)
                    tts_message.save(f"tts/{interaction.guild_id}.mp3")
                    audio = MP3(f"tts/{interaction.guild_id}.mp3")

                    try:
                        vc = await interaction.user.voice.channel.connect()
                    except:
                        for c in self.client.voice_clients:
                            if (
                                c.channel == interaction.user.voice.channel
                                and c.is_playing()
                            ):
                                await interaction.response.send_message(
                                    f"Please wait for the current TTS message to finish"
                                )
                                return
                            elif c.channel == interaction.user.voice.channel:
                                vc = c
                                break

                    embed = discord.Embed(
                        color=discord.Color.green(),
                        title="**Reading Message**",
                        description=f"Reading the message sent by {interaction.user.mention} in the voice channel {interaction.user.voice.channel.mention}",
                    )
                    await interaction.response.send_message(embed=embed)

                    assert isinstance(vc, discord.VoiceClient)
                    player = vc.play(
                        discord.FFmpegPCMAudio(
                            source=f"tts/{interaction.guild_id}.mp3"
                        ),
                        after=lambda e: 1 + 1,
                    )
                    await asyncio.sleep(audio.info.length + 1)
                    if leave and data["tts:leave"] == "True":
                        await vc.disconnect()
                    os.remove(f"tts/{interaction.guild_id}.mp3")

                else:
                    await interaction.response.send_message(
                        "You must be in a voice channel to use this command"
                    )

            else:
                await interaction.response.send_message(
                    "You don't have the required role to use TTS"
                )

        return self.client.incr_counter("tts_play")

    @tts_commands.command()
    async def stop(self, interaction: discord.Interaction):
        """Stops the current TTS message & Makes the bot leave the voice channel"""
        for x in self.client.voice_clients:
            if x.guild.id == interaction.guild_id and interaction.guild_id:
                await x.disconnect()
                embed = discord.Embed(
                    colour=discord.Color.green(),
                    description="The current TTS message has been stopped.",
                )
                await interaction.response.send_message(embed=embed)
                return self.client.incr_counter("tts_stop")

        embed = discord.Embed(
            colour=discord.Color.green(),
            description="There are no TTS messages being read at the minute",
        )
        await interaction.response.send_message(embed=embed)

        return self.client.incr_counter("tts_stop")

    @tts_commands.command()
    @app_commands.describe(
        enabled="Whether or not TTS is enabled in this server",
        role="The role required to use TTS (Default: None)",
        leave="Whether the bot leaves the voice channel after reading the message (Default: True)",
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        role: Optional[discord.Role] = None,
        leave: Optional[bool] = True,
    ):
        """Used to enable/disable TTS & set a required role"""
        await self.client._has_permissions(interaction, administrator=True)

        data = self.client.redis.get_guild_data(interaction.guild_id)

        data["tts:enabled"] = str(enabled)
        data["tts:role"] = str(role.id) if role else "None"
        data["tts:leave"] = str(leave)

        self.client.redis.update_guild_data(interaction.guild_id, data)

        await interaction.response.send_message(
            f"TTS settings updated: Enabled {enabled}, Role {role}, Leave {leave}"
        )

        return self.client.incr_counter("tts_setup")


async def setup(client: MyClient):
    await client.add_cog(TTS(client))
