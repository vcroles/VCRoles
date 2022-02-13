from datetime import datetime
import discord
from discord.ext import commands, tasks
import json
import os
import redis
import time
import logging

from utils import RedisUtils
from views.interface import Interface

with open("Data/config.json", "r") as f:
    config = json.load(f)

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


class MyClient(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        r = redis.Redis(
            host=config["REDIS"]["HOST"],
            port=config["REDIS"]["PORT"],
            db=config["REDIS"]["DB"],
            password=config["REDIS"]["PASSWORD"],
        )
        self.redis = RedisUtils(r)
        self.persistent_views_added = False

    async def on_ready(self):
        if not self.persistent_views_added:
            self.add_view(Interface(self.redis))
            self.persistent_views_added = True

        await self.change_presence(status=discord.Status.online)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="Voice Channels"
            )
        )

        print(f"Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds.")
        print("------")

        reminder.start()

    async def on_guild_remove(self, guild: discord.Guild):
        self.redis.guild_remove(guild.id)

    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error
    ):

        if isinstance(error, commands.MissingPermissions):
            await ctx.respond(
                "You do not have the required permissions to use this command.",
                ephemeral=True,
            )

        if isinstance(error, commands.NotOwner):
            await ctx.respond("This is a developer only command.", ephemeral=True)

        else:
            try:
                await ctx.respond(f"Error: {error}", ephemeral=True)
            except:
                pass

    async def on_command_error(self, ctx, error):
        return

    async def on_error(self, event, *args, **kwargs):
        with open("error.log", "a") as f:
            f.write(
                f"{datetime.utcnow().strftime('%m/%d/%Y, %H:%M:%S')} {event}: {str(args).encode('utf-8')}\n"
            )

    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        # Voice Channels
        if isinstance(channel, discord.VoiceChannel):
            data = self.redis.get_linked("voice", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("voice", channel.guild.id, data)

            data = self.redis.get_linked("permanent", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("permanent", channel.guild.id, data)

            data = self.redis.get_linked("all", channel.guild.id)
            if str(channel.id) in data["except"]:
                data["except"].remove(str(channel.id))
                self.redis.update_linked("all", channel.guild.id, data)

        # Stage Channels
        if isinstance(channel, discord.StageChannel):
            data = self.redis.get_linked("stage", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("stage", channel.guild.id, data)

        # Category Channels
        if isinstance(channel, discord.CategoryChannel):
            data = self.redis.get_linked("category", channel.guild.id)
            if str(channel.id) in data:
                del data[str(channel.id)]
                self.redis.update_linked("category", channel.guild.id, data)

    async def send_reminder(self):
        guild = await client.fetch_guild(775477268893270027)
        for hook in await guild.webhooks():
            if hook.channel.id == 869494079745056808 and hook.token:
                embed = discord.Embed(
                    title="Vote for VC Roles Here",
                    description="https://top.gg/bot/775025797034541107/vote/",
                    color=discord.Color.blue(),
                )
                await hook.send(
                    embeds=[embed],
                    username="VC Roles Top.gg",
                    avatar_url="https://avatars.githubusercontent.com/u/34552786",
                )


intents = discord.Intents(messages=True, guilds=True, reactions=True, voice_states=True)

client = MyClient(intents=intents, command_prefix=commands.when_mentioned_or("#"))
client.remove_command("help")

try:
    import topgg

    dbl_token = config["DBL_TOKEN"]
    client.topggpy = topgg.DBLClient(
        client, dbl_token, autopost=True, post_shard_count=True
    )
except ImportError:
    pass


@client.event
async def on_autopost_success():
    print(
        f"Posted server count ({client.topggpy.guild_count}), shard count ({client.shard_count})"
    )


# COMMANDS

# DEV Commands
@client.command(description="DEVELOPER COMMAND")
@commands.is_owner()
async def load(ctx, extension: str):
    try:
        client.load_extension(f"cogs.{extension}")
        await ctx.send(f"Successfully loaded {extension}")
    except:
        await ctx.send(f"Failed while loading {extension}")


@client.command(description="DEVELOPER COMMAND")
@commands.is_owner()
async def unload(ctx, extension: str):
    try:
        client.unload_extension(f"cogs.{extension}")
        await ctx.send(f"Successfully unloaded {extension}")
    except:
        await ctx.send(f"Failed while unloading {extension}")


@client.command(description="DEVELOPER COMMAND")
@commands.is_owner()
async def reload(ctx, extension: str):
    try:
        client.reload_extension(f"cogs.{extension}")
        await ctx.send(f"Successfully reloaded {extension}")
    except:
        await ctx.send(f"Failed while reloading {extension}")


@tasks.loop(minutes=1)
async def reminder():
    if time.strftime("%H:%M") in ["00:00", "12:00"]:
        await client.send_reminder()

        with open("guilds.json", "r") as f:
            data = json.load(f)

        data[datetime.utcnow().strftime("%H:%M %d/%m/%Y")] = len(client.guilds)

        with open("guilds.json", "w") as f:
            json.dump(data, f)


@reminder.before_loop
async def before_reminder():
    await client.wait_until_ready()


if __name__ == "__main__":

    # Adding Extensions

    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            client.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded extension: {filename[:-3]}")

    # Removing TTS files

    for filename in os.listdir("tts"):
        if filename.endswith(".mp3"):
            os.remove(f"tts/{filename}")

    # Removing Logs

    with open("error.log", "w") as file:
        file.write("")

    # Setting up guild count

    try:
        with open("guilds.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        with open("guilds.json", "w") as f:
            json.dump({}, f)

    # Running the bot.

    client.run(config["BOT_TOKEN"])
