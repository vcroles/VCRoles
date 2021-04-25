import discord
from discord.ext import commands
from ds import ds
from gtts import gTTS
import ffmpeg
from mutagen.mp3 import MP3
import os
import asyncio

dis = ds()

class tts(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(aliases=['tts'])
    @commands.cooldown(1, 210, commands.BucketType.guild)
    async def tts_(self, ctx, *, message):
        discord_terminal = self.client.get_channel(791253552139206667)
        data = dis.jopen("tts")

        if str(ctx.guild.id) not in data:
            await discord_terminal.send("You youse ned to enabe tts\n - 𝕄𝕣 𝕄𝕒𝕤𝕜#5225")
            await ctx.send(embed=dis.e_embed(121))
        else:
            #Checking if the user has the role specifed during setup
            role = ctx.guild.get_role(data[str(ctx.guild.id)]["role"])
            if role in ctx.author.roles or role == None:
                if len(message) >= 250:
                    await ctx.send(embed=dis.e_embed(119))

                else:
                    try:
                        user=ctx.message.author
                        voice_channel=user.voice.channel
                    except:
                        voice_channel = None

                    if voice_channel!= None:
                        tts = gTTS(message)
                        tts.save(f"tts\\{ctx.guild.id}.mp3")
                        file = f'tts\\{ctx.guild.id}.mp3'
                        audio = MP3(file)
                        audio_info = audio.info    
                        counter = 0
                        duration = int(audio_info.length) + 2 # In seconds
                        # grab the user who sent the command
                        user=ctx.message.author
                        voice_channel=user.voice.channel
                        channel=None
                        # only play music if user is in a voice channel

                        # grab user's voice channel
                        channel=voice_channel
                        sending_embed = discord.Embed(color=discord.Color.green(),title="**Reading Message**",description=f"Reading the message sent by {ctx.author.mention} in the voice channel {channel.name}")
                        await ctx.send(embed=sending_embed)
                        # create StreamPlayer
                        vc= await channel.connect()
                        player = vc.play(discord.FFmpegPCMAudio(executable="C:\\ffmpeg\\bin\\ffmpeg.exe", source=file), after=lambda e: print(f'Read TTS message', e))
                        while not counter >= duration:
                            await asyncio.sleep(1)
                            counter = counter + 1
                        await vc.disconnect()
                        os.remove(f'tts\\{ctx.guild.id}.mp3')

                    else:
                        #User is not in a voice channel
                        await ctx.send(embed=dis.e_embed(120))
            else:
                #User does not have the role
                await ctx.send(embed=dis.e_embed(101))

        self.tts_.reset_cooldown(ctx) # Ignore Red Error. Code Works Perfectly.
        dis.counter('tts')

    @commands.command()
    async def stop(self, ctx):
        for x in self.client.voice_clients:
            if(x.guild == ctx.message.guild):
                await x.disconnect()
                embed = discord.Embed(colour=discord.Color.green(), description='The current TTS message has been stopped.')
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(colour=discord.Color.green(), description='There are no TTS messages being read at the minute')
                await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def ttssetup(self, ctx, enabled = None, role:discord.Role = None):
        true_aliases = ['y', 'true', 'Y']
        false_aliases = ['n', 'false', 'N']
        data = dis.jopen("tts")
        
        if enabled in true_aliases:
            if role == None:
                data[str(ctx.guild.id)] = {'role':role}
                setup_embed = discord.Embed(color=discord.Color.green(), title=f'**TTS Enabled**', description='Every user can use the command')
            else:
                data[str(ctx.guild.id)] = {'role':role.id}
                setup_embed = discord.Embed(color=discord.Color.green(), title=f'**TTS Enabled**',description=f'Linked to role: {role.mention}')
        elif enabled in false_aliases:
            data.pop(str(ctx.guild.id))
            setup_embed = discord.Embed(color=discord.Color.red(), title=f'**TTS Disabled**')
        elif enabled == None:
            setup_embed = discord.Embed(color=discord.Color.dark_gray(),title="**TTS Setup Help**")
            setup_embed.add_field(name="**Enabling**",value=f"To enable the TTS feature pass in either y or n in the command - `{dis.get_prefix(ctx.message)}ttssetup y`",inline=False)
            setup_embed.add_field(name="**Role**",value=f"To limit TTS to a certain role pass in the role after y/n - `{dis.get_prefix(ctx.message)}ttssetup y @Moderator`\nIf you want it to not be limited to a role leave it blank.",inline=False)

        dis.jdump("tts", data)
        await ctx.send(embed=setup_embed)
        dis.counter('ttssetup')

def setup(client):
    client.add_cog(tts(client))
