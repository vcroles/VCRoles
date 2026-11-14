import asyncio
import importlib
import shutil
import subprocess
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import discord
from discord.player import AudioPlayer

tts_module = importlib.import_module("cogs.tts")
TTS = tts_module.TTS


class TTSTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.channel = Mock()
        self.channel.mention = "#voice"
        self.guild = SimpleNamespace(id=1, voice_client=None)
        user = Mock(spec=discord.Member)
        user.id = 2
        user.mention = "@member"
        user.voice = SimpleNamespace(channel=self.channel)
        self.interaction = SimpleNamespace(
            guild=self.guild,
            guild_id=1,
            user=user,
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        self.settings = SimpleNamespace(ttsEnabled=True, ttsRole=None, ttsLeave=True)
        self.client = Mock()
        self.client.db.get_guild_data = AsyncMock(return_value=self.settings)
        self.cog = TTS(self.client)
        self.voice = Mock(spec=discord.VoiceClient)
        self.voice.channel = self.channel
        self.voice.is_playing.return_value = False
        self.voice.is_paused.return_value = False
        self.voice.move_to = AsyncMock()
        self.started = asyncio.Event()
        self.voice.play.side_effect = self.play
        self.voice.stop.side_effect = self.stop
        self.voice.disconnect = AsyncMock(side_effect=self.disconnect)
        self.channel.connect = AsyncMock(side_effect=self.connect)
        self.source = Mock()
        self.synthesis = AsyncMock(return_value=b"audio")
        self.after = None
        self.tasks = []
        for patcher in (
            patch.object(
                tts_module,
                "gTTSAsync",
                return_value=SimpleNamespace(get_audio_data=self.synthesis),
            ),
            patch.object(tts_module, "TTSAudioSource", return_value=self.source),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    async def asyncTearDown(self):
        for task in self.tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)

    async def connect(self):
        self.guild.voice_client = self.voice
        return self.voice

    async def disconnect(self, **kwargs):
        self.guild.voice_client = None

    def play(self, source, *, after):
        self.after = after
        self.voice.is_playing.return_value = True
        self.started.set()

    def complete(self, error=None):
        self.voice.is_playing.return_value = False
        self.voice.is_paused.return_value = False
        if self.after is not None:
            after, self.after = self.after, None
            after(error)
            # Discord's AudioPlayer releases the source on its audio thread.
            self.source.cleanup()

    def stop(self):
        self.complete()

    def start_command(self, *, leave=True):
        task = asyncio.create_task(
            TTS.play.callback(self.cog, self.interaction, "Hello", leave=leave)
        )
        self.tasks.append(task)
        return task

    async def test_success_waits_for_audio_thread_and_retains_connection_when_requested(
        self,
    ):
        task = self.start_command(leave=False)
        await asyncio.wait_for(self.started.wait(), 1)
        self.interaction.response.defer.assert_awaited_once()
        self.assertFalse(task.done())
        audio_thread = threading.Thread(target=self.complete)
        audio_thread.start()
        audio_thread.join(timeout=1)
        await asyncio.wait_for(task, 1)
        self.source.cleanup.assert_called()
        self.voice.disconnect.assert_not_awaited()
        self.assertFalse(self.cog.playback_tasks)

    async def test_default_play_disconnects_after_completion(self):
        task = self.start_command()
        await asyncio.wait_for(self.started.wait(), 1)
        self.complete()
        await asyncio.wait_for(task, 1)
        self.voice.disconnect.assert_awaited_once_with(force=True)

    async def test_unload_waits_for_delayed_cleanup_after_audio_callback(self):
        playing = self.start_command(leave=False)
        await asyncio.wait_for(self.started.wait(), 1)
        loop = asyncio.get_running_loop()
        cleaning = asyncio.Event()
        release = threading.Event()

        def delayed_cleanup():
            loop.call_soon_threadsafe(cleaning.set)
            if not release.wait(timeout=2):
                raise AssertionError("Cleanup was not released")

        self.source.cleanup.side_effect = delayed_cleanup
        audio_thread = threading.Thread(target=self.complete)
        audio_thread.start()
        try:
            await asyncio.wait_for(cleaning.wait(), 1)
            unloading = asyncio.create_task(self.cog.cog_unload())
            self.tasks.append(unloading)
            await asyncio.sleep(0)
            self.assertFalse(unloading.done())
            self.assertIn(self.guild.id, self.cog.playback_tasks)
        finally:
            release.set()
            await asyncio.to_thread(audio_thread.join, 1)
        await asyncio.wait_for(unloading, 1)
        await playing
        self.assertFalse(self.cog.playback_tasks)

    async def test_paused_playback_does_not_complete_or_disconnect(self):
        task = self.start_command()
        await asyncio.wait_for(self.started.wait(), 1)
        self.voice.is_playing.return_value = False
        self.voice.is_paused.return_value = True
        await asyncio.sleep(0)
        self.assertFalse(task.done())
        self.voice.disconnect.assert_not_awaited()
        self.complete()
        await asyncio.wait_for(task, 1)

    async def test_existing_paused_audio_is_rejected_without_synthesis(self):
        self.guild.voice_client = self.voice
        self.voice.is_paused.return_value = True
        await self.start_command()
        self.synthesis.assert_not_awaited()
        self.voice.disconnect.assert_not_awaited()

    async def test_synthesis_failure_does_not_disconnect_existing_idle_voice(self):
        self.guild.voice_client = self.voice
        self.synthesis.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError):
            await self.start_command()
        self.voice.disconnect.assert_not_awaited()
        self.assertFalse(self.cog.playback_tasks)

    async def test_new_playback_started_during_synthesis_is_not_interrupted(self):
        async def synthesize():
            self.guild.voice_client = self.voice
            self.voice.is_playing.return_value = True
            return b"audio"

        self.synthesis.side_effect = synthesize
        await self.start_command()
        self.voice.play.assert_not_called()
        self.voice.disconnect.assert_not_awaited()

    async def test_concurrent_commands_allow_only_one_worker(self):
        synthesizing = asyncio.Event()
        release = asyncio.Event()

        async def synthesize():
            synthesizing.set()
            await release.wait()
            return b"audio"

        self.synthesis.side_effect = synthesize
        first = self.start_command()
        await asyncio.wait_for(synthesizing.wait(), 1)
        await self.start_command()
        self.synthesis.assert_awaited_once()
        release.set()
        await asyncio.wait_for(self.started.wait(), 1)
        self.complete()
        await asyncio.wait_for(first, 1)

    async def test_stop_during_synthesis_prevents_voice_connection(self):
        synthesizing = asyncio.Event()

        async def synthesize():
            synthesizing.set()
            await asyncio.Event().wait()

        self.synthesis.side_effect = synthesize
        playing = self.start_command()
        await asyncio.wait_for(synthesizing.wait(), 1)
        await TTS.stop.callback(self.cog, self.interaction)
        await asyncio.wait_for(playing, 1)
        self.channel.connect.assert_not_awaited()
        self.assertFalse(self.cog.playback_tasks)
        self.assertFalse(self.cog.stopping_guilds)

    async def test_stop_during_playback_releases_source_and_disconnects(self):
        playing = self.start_command(leave=False)
        await asyncio.wait_for(self.started.wait(), 1)
        await TTS.stop.callback(self.cog, self.interaction)
        await asyncio.wait_for(playing, 1)
        self.voice.stop.assert_called_once()
        self.source.cleanup.assert_called()
        self.voice.disconnect.assert_awaited_once()

    async def test_missing_stop_callback_forces_audio_cleanup(self):
        self.cog.PLAYBACK_STOP_TIMEOUT = 0.01
        self.voice.stop.side_effect = lambda: setattr(
            self.voice.is_playing, "return_value", False
        )
        playing = self.start_command(leave=False)
        await asyncio.wait_for(self.started.wait(), 1)
        await asyncio.wait_for(TTS.stop.callback(self.cog, self.interaction), 1)
        await playing
        self.source.cleanup.assert_called()
        self.voice.disconnect.assert_awaited_once()
        self.client.log.assert_any_call(
            tts_module.LogLevel.ERROR,
            "TTS audio thread did not stop in time",
            event="tts_stop_timeout",
            **self.cog.log_context(self.interaction, self.channel),
        )

    async def test_cancel_during_handshake_recovers_registered_voice_client(self):
        connecting = asyncio.Event()

        async def connect():
            self.guild.voice_client = self.voice
            connecting.set()
            await asyncio.Event().wait()

        self.channel.connect.side_effect = connect
        playing = self.start_command()
        await asyncio.wait_for(connecting.wait(), 1)
        await self.cog.cog_unload()
        await asyncio.wait_for(playing, 1)
        self.voice.disconnect.assert_awaited_once()

    async def test_cleanup_failure_is_logged_after_cancellation_during_cleanup(self):
        disconnecting = asyncio.Event()
        release = asyncio.Event()
        failure = RuntimeError("disconnect failed")

        async def disconnect(**kwargs):
            disconnecting.set()
            await release.wait()
            raise failure

        self.voice.disconnect.side_effect = disconnect
        playing = self.start_command()
        await asyncio.wait_for(self.started.wait(), 1)
        self.complete()
        await asyncio.wait_for(disconnecting.wait(), 1)
        playing.cancel()
        await asyncio.sleep(0)
        release.set()
        with self.assertRaisesRegex(RuntimeError, "disconnect failed"):
            await asyncio.wait_for(playing, 1)
        self.client.log.assert_any_call(
            tts_module.LogLevel.ERROR,
            "TTS cleanup failed",
            error=failure,
            event="tts_cleanup_failed",
            **self.cog.log_context(self.interaction, self.channel),
        )
        self.assertFalse(self.cog.playback_tasks)

    async def test_unload_during_database_lookup_prevents_late_worker(self):
        looking_up = asyncio.Event()
        release = asyncio.Event()

        async def lookup(*args):
            looking_up.set()
            await release.wait()
            return self.settings

        self.client.db.get_guild_data.side_effect = lookup
        playing = self.start_command()
        await asyncio.wait_for(looking_up.wait(), 1)
        await self.cog.cog_unload()
        release.set()
        await asyncio.wait_for(playing, 1)
        self.synthesis.assert_not_awaited()

    async def test_playback_error_propagates_and_disconnects(self):
        playing = self.start_command(leave=False)
        await asyncio.wait_for(self.started.wait(), 1)
        self.complete(RuntimeError("FFmpeg failed"))
        with self.assertRaisesRegex(RuntimeError, "FFmpeg failed"):
            await playing
        self.source.cleanup.assert_called()
        self.voice.disconnect.assert_awaited_once()

    async def test_leaving_channel_during_synthesis_does_not_connect(self):
        async def synthesize():
            self.interaction.user.voice = None
            return b"audio"

        self.synthesis.side_effect = synthesize
        await self.start_command()
        self.channel.connect.assert_not_awaited()

    async def test_play_failure_releases_source_without_interrupting_other_audio(self):
        def other_audio(*args, **kwargs):
            self.voice.is_playing.return_value = True
            raise discord.ClientException("Already playing")

        self.voice.play.side_effect = other_audio
        with self.assertRaises(discord.ClientException):
            await self.start_command()
        self.source.cleanup.assert_called()
        self.voice.disconnect.assert_not_awaited()


class RealAudioSourceTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required")
    def test_failed_ffmpeg_stderr_is_logged_with_operation_context(self):
        source = tts_module.TTSAudioSource(
            b"invalid mp3", log_context={"guild_id": 123}
        )
        try:
            source._process.wait(timeout=2)
            with self.assertLogs(tts_module.__name__, level="ERROR") as captured:
                source.cleanup()
        finally:
            source.cleanup()
        record = captured.records[0]
        self.assertEqual(record.event, "tts_ffmpeg_failed")
        self.assertEqual(record.context["guild_id"], 123)
        self.assertTrue(record.context["stderr_tail"])
        self.assertNotEqual(record.context["return_code"], 0)
        self.assertTrue(source.diagnostics.closed)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required")
    def test_real_ffmpeg_reads_mp3_and_releases_input_buffer(self):
        audio = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "0.1",
                "-f",
                "mp3",
                "pipe:1",
            ]
        )
        source = tts_module.TTSAudioSource(audio)
        try:
            self.assertFalse(source.buffer.closed)
            self.assertTrue(source.read())
            self.assertTrue(source.is_opus())
        finally:
            source.cleanup()
        self.assertTrue(source.buffer.closed)

    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required")
    def test_cancel_long_input_reaps_process_and_pipe_writer(self):
        audio = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "30",
                "-f",
                "mp3",
                "pipe:1",
            ]
        )
        failures = []
        with patch.object(threading, "excepthook", side_effect=failures.append):
            source = tts_module.TTSAudioSource(audio)
            process = source._process
            writer = source._pipe_writer_thread
            try:
                source.cleanup()
                source.cleanup()
                self.assertIsNotNone(process.poll())
                self.assertFalse(writer.is_alive())
                self.assertTrue(source.buffer.closed)
                self.assertFalse(failures)
            finally:
                source.cleanup()


class RealAudioPlayerTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg is required")
    async def test_audio_thread_owns_cleanup_on_completion_and_cancellation(self):
        audio = subprocess.check_output(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "0.1",
                "-f",
                "mp3",
                "pipe:1",
            ]
        )
        loop = asyncio.get_running_loop()
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                source = tts_module.TTSAudioSource(audio)
                process = source._process
                writer = source._pipe_writer_thread
                done = loop.create_future()
                sent = asyncio.Event()

                def packet(*args, sent=sent, **kwargs):
                    loop.call_soon_threadsafe(sent.set)

                def after(error, done=done):
                    loop.call_soon_threadsafe(done.set_result, error)

                voice = SimpleNamespace(
                    ws=SimpleNamespace(speak=AsyncMock()),
                    client=SimpleNamespace(loop=loop),
                    send_audio_packet=packet,
                    is_connected=lambda: True,
                )
                player = AudioPlayer(source, voice, after=after)
                player.start()
                try:
                    await asyncio.wait_for(sent.wait(), 2)
                    if cancel:
                        player.stop()
                    self.assertIsNone(await asyncio.wait_for(done, 2))
                finally:
                    player.stop()
                    await asyncio.to_thread(player.join, 3)
                self.assertFalse(player.is_alive())
                self.assertFalse(writer.is_alive())
                self.assertIsNotNone(process.poll())
                self.assertTrue(source.buffer.closed)
