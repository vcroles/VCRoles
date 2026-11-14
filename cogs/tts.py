import asyncio
import io
import logging
import subprocess
import tempfile
import threading
from time import monotonic
from typing import Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands
from gtts import gTTSAsync

from utils.checks import check_any, command_available, is_owner
from utils.client import VCRolesClient
from utils.telemetry import get_telemetry, observed
from utils.types import LogLevel

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


class TTSAudioSource(discord.FFmpegOpusAudio):
    """Keep the input buffer alive until the audio thread releases FFmpeg."""

    def __init__(self, audio_data: bytes, *, log_context=None):
        self.cleanup_lock = threading.Lock()
        self.cleaned = False
        self.log_context = log_context or {}
        self.telemetry_context = get_telemetry().capture_context()
        self.buffer = io.BytesIO(audio_data)
        self.diagnostics = None
        try:
            self.diagnostics = tempfile.TemporaryFile(mode="w+b")
            super().__init__(
                source=self.buffer,
                before_options="-f mp3",
                pipe=True,
                stderr=self.diagnostics,
            )
        except BaseException:
            self.cleanup()
            raise

    def cleanup(self):
        with (
            get_telemetry().operation(
                "tts", "audio_cleanup", links=[getattr(self, "telemetry_context", None)]
            ),
            self.cleanup_lock,
        ):
            if self.cleaned:
                return
            self.cleaned = True
            process = getattr(self, "_process", None)
            writer = getattr(self, "_pipe_writer_thread", None)
            return_code = (
                process.poll() if isinstance(process, subprocess.Popen) else None
            )
            try:
                # Stop and join the writer before the fork replaces _process
                # with MISSING. Otherwise its broken-pipe handler races cleanup.
                if isinstance(process, subprocess.Popen):
                    process.kill()
                    process.wait(timeout=5)
                if writer is not None and writer is not threading.current_thread():
                    writer.join(timeout=1)
            finally:
                try:
                    super().cleanup()
                finally:
                    if isinstance(process, subprocess.Popen):
                        for stream in (
                            process.stdin,
                            process.stdout,
                            process.stderr,
                        ):
                            if stream is not None:
                                try:
                                    stream.close()
                                except OSError:
                                    # Buffered stdin may flush into a killed process.
                                    pass
                    self.buffer.close()
                    if self.diagnostics is not None:
                        try:
                            if return_code not in (None, 0):
                                self.diagnostics.seek(0, io.SEEK_END)
                                self.diagnostics.seek(
                                    max(0, self.diagnostics.tell() - 8192)
                                )
                                logging.getLogger(__name__).error(
                                    "FFmpeg exited with an error",
                                    extra={
                                        "event": "tts_ffmpeg_failed",
                                        "context": {
                                            **self.log_context,
                                            "return_code": return_code,
                                            "stderr_tail": self.diagnostics.read().decode(
                                                "utf-8", errors="replace"
                                            ),
                                        },
                                    },
                                )
                        finally:
                            self.diagnostics.close()


class TTS(commands.Cog):
    PLAYBACK_STOP_TIMEOUT = 5

    def __init__(self, client: VCRolesClient):
        self.client = client
        self.playback_tasks: dict[int, asyncio.Task] = {}
        self.stopping_guilds: set[int] = set()
        self.unloading = False

    tts_commands = app_commands.Group(name="tts", description="Text To Speech commands")

    @tts_commands.command()
    @app_commands.describe(
        message="Enter the message you want to read",
        language="Enter the language you want to use (Default: English `en: English`)",
        leave="The bot leaves the voice channel after reading the message (Default: True)",
    )
    @observed("command")
    async def play(
        self,
        interaction: discord.Interaction,
        message: str,
        language: tts_langs = "en: English",
        leave: bool = True,
    ):
        """Used to make the bot read a message in a voice channel"""
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        if not interaction.user.voice or not interaction.user.voice.channel:
            return await interaction.response.send_message(
                "You must be in a voice channel to use this command."
            )

        channel = interaction.user.voice.channel
        await interaction.response.defer()

        guild_id = interaction.guild.id
        if self.unloading:
            return await interaction.followup.send(
                "TTS is shutting down. Please try again shortly."
            )
        if guild_id in self.playback_tasks or guild_id in self.stopping_guilds:
            return await interaction.followup.send(
                "Please wait for the current TTS message to finish."
            )
        task = asyncio.create_task(
            self._prepare_play(
                interaction,
                channel,
                message,
                language.split(":", 1)[0],
                leave,
            )
        )
        self.playback_tasks[guild_id] = task
        try:
            await task
        except asyncio.CancelledError:
            # /tts stop and cog unload cancel the playback worker.
            current = asyncio.current_task()
            if current is not None and current.cancelling():
                raise
            if not self.unloading:
                await interaction.followup.send("TTS playback stopped.")
        finally:
            if self.playback_tasks.get(guild_id) is task:
                del self.playback_tasks[guild_id]

    @observed("tts")
    async def _prepare_play(
        self, interaction, channel, message: str, language: str, leave: bool
    ):
        try:
            guild_data = await self.client.db.get_guild_data(interaction.guild.id)
        except Exception as error:
            self.client.log(
                LogLevel.ERROR,
                "TTS settings lookup failed",
                error=error,
                event="tts_preparation_failed",
                **self.log_context(interaction, channel),
            )
            raise
        if not guild_data.ttsEnabled:
            return await interaction.followup.send("TTS isn't enabled in this server.")
        if len(message) > 250 and interaction.user.id not in [
            652797071623192576,
            602235481459261440,
        ]:
            return await interaction.followup.send(
                "The message is over the 250 character limit"
            )
        if guild_data.ttsRole and not interaction.user.get_role(
            int(guild_data.ttsRole)
        ):
            return await interaction.followup.send(
                "You don't have the required role to use TTS"
            )

        await self._play(
            interaction, channel, message, language, leave and guild_data.ttsLeave
        )

    @staticmethod
    def log_context(interaction, channel):
        return {
            "interaction_id": getattr(interaction, "id", None),
            "guild_id": interaction.guild.id,
            "member_id": interaction.user.id,
            "shard_id": getattr(interaction.guild, "shard_id", None),
            "voice_channel_id": channel.id,
        }

    @observed("tts")
    async def _play(
        self, interaction, channel, message: str, language: str, leave: bool
    ):
        vc = interaction.guild.voice_client
        if vc and (
            not isinstance(vc, discord.VoiceClient) or vc.is_playing() or vc.is_paused()
        ):
            return await interaction.followup.send(
                "Please wait for the current audio to finish."
            )
        context = self.log_context(interaction, channel)
        started_at = monotonic()
        phase = "synthesis"
        self.client.log(
            LogLevel.INFO, "TTS request started", event="tts_started", **context
        )
        completed = False
        claimed_voice = False
        started = False
        source = None
        loop = asyncio.get_running_loop()
        playback_done = loop.create_future()

        def finish(error):
            if not playback_done.done():
                playback_done.set_result(error)

        def after(error):
            loop.call_soon_threadsafe(finish, error)

        try:
            with get_telemetry().operation("tts", "synthesis"):
                audio_data = await asyncio.wait_for(
                    gTTSAsync(text=message, lang=language).get_audio_data(), timeout=30
                )
            if not interaction.user.voice or interaction.user.voice.channel != channel:
                return await interaction.followup.send(
                    "You left the voice channel before playback started."
                )
            # Synthesis yields to other commands. Inspect the current voice
            # client again before acquiring or moving any connection.
            vc = interaction.guild.voice_client
            if vc and (
                not isinstance(vc, discord.VoiceClient)
                or vc.is_playing()
                or vc.is_paused()
            ):
                return await interaction.followup.send(
                    "Please wait for the current audio to finish."
                )
            claimed_voice = True
            phase = "voice_connect"
            with get_telemetry().operation("tts", "voice_connect"):
                if vc is None:
                    vc = await channel.connect()
                elif vc.channel != channel:
                    await vc.move_to(channel)
            if not interaction.user.voice or interaction.user.voice.channel != channel:
                return await interaction.followup.send(
                    "You left the voice channel before playback started."
                )

            phase = "playback"
            with get_telemetry().operation("tts", "playback"):
                source = TTSAudioSource(audio_data, log_context=context)
                vc.play(source, after=after)
                started = True
                await interaction.followup.send(
                    embed=discord.Embed(
                        color=discord.Color.green(),
                        title="**Reading Message**",
                        description=f"Reading the message sent by {interaction.user.mention} in {channel.mention}",
                    )
                )
                error = await asyncio.shield(playback_done)
                if error is not None:
                    raise error
                completed = True
        except asyncio.CancelledError:
            self.client.log(
                LogLevel.INFO,
                "TTS request cancelled",
                event="tts_cancelled",
                phase=phase,
                **context,
            )
            raise
        except Exception as error:
            self.client.log(
                LogLevel.ERROR,
                "TTS request failed",
                error=error,
                event="tts_failed",
                phase=phase,
                **context,
            )
            raise
        finally:

            async def cleanup():
                # connect() registers the client before its handshake finishes.
                voice_client = vc
                if claimed_voice:
                    voice_client = vc or interaction.guild.voice_client
                if started and not playback_done.done():
                    if voice_client:
                        voice_client.stop()
                    try:
                        await asyncio.wait_for(
                            asyncio.shield(playback_done), self.PLAYBACK_STOP_TIMEOUT
                        )
                    except TimeoutError:
                        self.client.log(
                            LogLevel.ERROR,
                            "TTS audio thread did not stop in time",
                            event="tts_stop_timeout",
                            **context,
                        )
                # Discord invokes after() before releasing the source. Always
                # join its idempotent cleanup, including successful playback.
                if source is not None:
                    await asyncio.to_thread(source.cleanup)
                if (
                    claimed_voice
                    and voice_client
                    and (leave or not completed)
                    and not (voice_client.is_playing() or voice_client.is_paused())
                ):
                    await voice_client.disconnect(force=True)

            async def logged_cleanup():
                with get_telemetry().operation("tts", "cleanup"):
                    try:
                        await cleanup()
                    except Exception as error:
                        self.client.log(
                            LogLevel.ERROR,
                            "TTS cleanup failed",
                            error=error,
                            event="tts_cleanup_failed",
                            **context,
                        )
                        raise

            cleanup_task = asyncio.create_task(logged_cleanup())
            try:
                await asyncio.shield(cleanup_task)
            except asyncio.CancelledError:
                # Stop/unload may cancel a request already in final cleanup.
                # Keep its reservation until FFmpeg and the connection finish.
                await cleanup_task
                raise

        self.client.log(
            LogLevel.INFO,
            "TTS request completed",
            event="tts_completed",
            duration_ms=round((monotonic() - started_at) * 1000, 3),
            **context,
        )

    @tts_commands.command()
    @observed("command")
    async def stop(self, interaction: discord.Interaction):
        """Stops the current TTS message & makes the bot leave the voice channel"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )
        await interaction.response.defer()
        if interaction.guild.id in self.stopping_guilds:
            return await interaction.followup.send("TTS is already stopping.")
        task = self.playback_tasks.get(interaction.guild.id)
        vc = interaction.guild.voice_client
        self.stopping_guilds.add(interaction.guild.id)
        try:
            if task:
                if not task.cancelling():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            vc = interaction.guild.voice_client
            if vc:
                await vc.disconnect(force=True)
        finally:
            self.stopping_guilds.discard(interaction.guild.id)
        await interaction.followup.send(
            "The current TTS message has been stopped."
            if task or vc
            else "There are no TTS messages being read at the minute."
        )
        self.client.log(
            LogLevel.INFO,
            "TTS stopped",
            event="tts_stopped",
            guild_id=interaction.guild_id,
            member_id=interaction.user.id,
            interaction_id=getattr(interaction, "id", None),
        )

    async def cog_unload(self):
        self.unloading = True
        tasks = list(self.playback_tasks.values())
        for task in tasks:
            if not task.cancelling():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await super().cog_unload()

    @tts_commands.command()
    @app_commands.describe(
        enabled="Whether or not TTS is enabled in this server",
        role="The role required to use TTS (Default: None)",
        leave="Whether the bot leaves the voice channel after reading the message (Default: True)",
    )
    @check_any(command_available, is_owner)
    @app_commands.checks.has_permissions(administrator=True)
    @observed("command")
    async def setup(
        self,
        interaction: discord.Interaction,
        enabled: bool,
        role: Optional[discord.Role] = None,
        leave: Optional[bool] = True,
    ):
        """Used to enable/disable TTS & set a required role"""

        if not interaction.guild:
            return await interaction.response.send_message(
                "You must be in a server to use this command."
            )

        await self.client.db.update_guild_data(
            interaction.guild.id,
            tts_enabled=enabled,
            tts_leave=leave,
            tts_role=str(role.id) if role else "None",
        )

        await interaction.response.send_message(
            f"TTS settings updated: Enabled {enabled}, Role {role}, Leave {leave}"
        )

        self.client.log(
            LogLevel.DEBUG,
            f"TTS setup: g/{interaction.guild.id} m/{interaction.user.id}",
        )


async def setup(client: VCRolesClient):
    await client.add_cog(TTS(client))
