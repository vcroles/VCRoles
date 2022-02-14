import discord, os, asyncio
from discord.commands import Option
from discord.ext import commands
from gtts import gTTS
from mutagen.mp3 import MP3
from bot import MyClient
from utils import Permissions

tts_langs = [
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

    @commands.slash_command(
        description="Used to make the bot read a message in a voice channel"
    )
    async def tts(
        self,
        ctx: discord.ApplicationContext,
        message: Option(str, "Message to read."),
        language: Option(
            str,
            "Language to read in",
            choices=tts_langs,
            default="en: English",
            required=False,
        ),
        leave: Option(
            bool,
            "Whether the bot leaves the voice channel after reading",
            default=True,
            required=False,
        ),
    ):
        index = language.find(":")
        language_code = language[0:index]

        data = self.client.redis.get_guild_data(ctx.guild.id)

        if data["tts:enabled"] == "False":
            await ctx.respond(f"TTS isn't enabled in this server.")
            return
        if len(message) > 250:
            await ctx.respond(f"The message is over the 250 character limit")
            return
        if data["tts:enabled"] == "True":

            try:
                role = ctx.guild.get_role(int(data["tts:role"]))
            except:
                role = None

            if role in ctx.author.roles or data["tts:role"] == "None":
                if ctx.author.voice.channel:
                    tts_message = gTTS(text=message, lang=language_code)
                    tts_message.save(f"tts/{ctx.guild.id}.mp3")
                    audio = MP3(f"tts/{ctx.guild.id}.mp3")

                    try:
                        vc = await ctx.author.voice.channel.connect()
                    except:
                        for c in self.client.voice_clients:
                            if (
                                c.channel == ctx.author.voice.channel
                                and c.is_playing() == True
                            ):
                                await ctx.respond(
                                    f"Please wait for the current TTS message to finish"
                                )
                                return
                            elif c.channel == ctx.author.voice.channel:
                                vc = c
                                break

                    embed = discord.Embed(
                        color=discord.Color.green(),
                        title="**Reading Message**",
                        description=f"Reading the message sent by {ctx.author.mention} in the voice channel {ctx.author.voice.channel.mention}",
                    )
                    await ctx.respond(embed=embed)

                    player = vc.play(
                        discord.FFmpegPCMAudio(source=f"tts/{ctx.guild.id}.mp3"),
                        after=lambda e: 1 + 1,
                    )
                    await asyncio.sleep(audio.info.length + 1)
                    if leave == True:
                        await vc.disconnect()
                    os.remove(f"tts/{ctx.guild.id}.mp3")

                else:
                    await ctx.respond(
                        "You must be in a voice channel to use this command"
                    )

            else:
                await ctx.respond("You don't have the required role to use TTS")

    @commands.slash_command(
        description="Stops the current TTS message & Makes the bot leave the voice channel"
    )
    async def ttsstop(self, ctx: discord.ApplicationContext):
        for x in self.client.voice_clients:
            if x.guild == ctx.guild:
                await x.disconnect()
                embed = discord.Embed(
                    colour=discord.Color.green(),
                    description="The current TTS message has been stopped.",
                )
                await ctx.respond(embed=embed)
                return

        embed = discord.Embed(
            colour=discord.Color.green(),
            description="There are no TTS messages being read at the minute",
        )
        await ctx.respond(embed=embed)

    @commands.slash_command(
        description="Used to enable/disable TTS & set a required role"
    )
    @Permissions.has_permissions(administrator=True)
    async def ttssetup(
        self,
        ctx: discord.ApplicationContext,
        enabled: Option(bool, "Whether TTS is enabled"),
        role: Option(
            discord.Role, "A role required to use TTS", required=False, default=None
        ),
    ):
        data = self.client.redis.get_guild_data(ctx.guild.id)

        if role:
            data["tts:enabled"] = str(enabled)
            data["tts:role"] = str(role.id)
        else:
            data["tts:enabled"] = str(enabled)
            data["tts:role"] = str(role)

        self.client.redis.update_guild_data(ctx.guild.id, data)

        await ctx.respond(f"TTS settings updated: Enabled {enabled}, Role {role}")


def setup(client: MyClient):
    client.add_cog(TTS(client))
