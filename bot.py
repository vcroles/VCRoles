import asyncio
import datetime as dt
import json
import logging
import os
from typing import Optional

import discord
import redis
import redis.asyncio as aioredis
from discord import app_commands
from discord.ext import commands, tasks

import config
from utils import RedisUtils
from views.interface import Interface
from views.url import TopGG

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
        redis_url = f"redis://:{config.REDIS.PASSWORD}@{config.REDIS.HOST}:{config.REDIS.PORT}/{config.REDIS.DB}"
        r = redis.from_url(redis_url)
        self.ar = aioredis.from_url(redis_url)
        self.redis = RedisUtils(r)
        self.persistent_views_added = False

    def incr_counter(self, cmd_name: str):
        """Increments the counter for a command"""
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", cmd_name, 1)
        )

    def incr_role_counter(self, action: str, count: int = 1):
        """
        action: `add` or `remove`.
        Increments the counter for roles added or removed
        """
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", f"roles_{action}", count)
        )

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

    async def setup_hook(self):
        reminder.start()

    async def on_guild_join(self, guild: discord.Guild):
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", "guilds_join", 1)
        )

    async def on_guild_remove(self, guild: discord.Guild):
        self.loop.create_task(
            self.ar.execute_command("hincrby", "counters", "guilds_leave", 1)
        )
        self.redis.guild_remove(guild.id)

    async def on_command_error(self, ctx, error):
        return

    async def on_error(self, event, *args, **kwargs):
        with open("error.log", "a") as f:
            f.write(
                f"{discord.utils.utcnow().strftime('%m/%d/%Y, %H:%M:%S')} {event}: {str(args).encode('utf-8')=}: {str(kwargs).encode('utf-8')=}\n"
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
                    description="Vote & get unlimited command usage!\nhttps://top.gg/bot/775025797034541107/vote/",
                    color=discord.Color.blue(),
                    url="https://top.gg/bot/775025797034541107/vote/",
                )
                await hook.send(
                    embeds=[embed],
                    username="VC Roles Top.gg",
                    avatar_url="https://avatars.githubusercontent.com/u/34552786",
                )


intents = discord.Intents(messages=True, guilds=True, reactions=True, voice_states=True)

client = MyClient(intents=intents, command_prefix=commands.when_mentioned)
client.remove_command("help")


@client.event
async def on_autopost_success():
    print(
        f"Posted server count ({client.topggpy.guild_count}), shard count ({client.shard_count})"
    )


@client.event
async def on_dbl_vote(data):
    if data["type"] == "upvote":
        client.loop.create_task(
            client.ar.execute_command("hset", "commands", str(data["user"]), -10_000)
        )

        user = await client.fetch_user(int(data["user"]))

        channel = client.get_channel(947070091797856276)
        embed = discord.Embed(
            colour=discord.Colour.blue(),
            title=":tada: Top.gg Vote! :tada:",
            description=f"{user.mention} ({user.name}) just voted for VC Roles on Top.gg & received unlimited command usage for the rest of the day!\n\nClick [here](https://top.gg/bot/775025797034541107/vote) to vote",
            url="https://top.gg/bot/775025797034541107/vote",
        )
        embed.set_thumbnail(url=user.avatar.url)
        embed.set_footer(text="Thanks for voting!")
        await channel.send(embed=embed)
    else:
        print(data)


@client.tree.error
async def on_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError,
):
    if isinstance(error, app_commands.MissingPermissions):
        return await interaction.response.send_message(
            "You do not have the required permissions to use this command.",
            ephemeral=True,
        )
    if isinstance(error, app_commands.CheckFailure):
        embed = discord.Embed(
            title="Command Limit Reached",
            description=f"You have reached your command limit for today, but **don't worry!** You can get **unlimited** command usage for the rest of the day by [voting for the bot on Top.gg!](https://top.gg/bot/775025797034541107/vote)",
            colour=discord.Colour.brand_red(),
            url="https://top.gg/bot/775025797034541107/vote",
        )
        embed.set_thumbnail(url=interaction.user.avatar.url)
        embed.set_author(name=client.user.name, icon_url=client.user.avatar.url)
        embed.set_footer(text="Thanks for using the bot!")

        return await interaction.response.send_message(
            embed=embed, ephemeral=True, view=TopGG()
        )
    else:
        return


@tasks.loop(time=[dt.time(hour=12, minute=0), dt.time(hour=0, minute=0)])
async def reminder():
    client.loop.create_task(client.send_reminder())

    with open("guilds.json", "r") as f:
        data = json.load(f)

    data[discord.utils.utcnow().strftime("%H:%M %d/%m/%Y")] = len(client.guilds)

    with open("guilds.json", "w") as f:
        json.dump(data, f)

    if dt.datetime.utcnow().strftime("%H:%M") == "00:00":
        client.loop.create_task(client.ar.execute_command("del", "commands"))


@reminder.before_loop
async def before_reminder():
    await client.wait_until_ready()


async def main():

    # Removing TTS files

    for filename in os.listdir("tts"):
        if filename.endswith(".mp3"):
            os.remove(f"tts/{filename}")

    # Removing Logs

    with open("error.log", "w") as file:
        file.write("")

    # Removing Export Files

    for filename in os.listdir("exports"):
        if filename.endswith(".json"):
            os.remove(f"exports/{filename}")

    # Setting up guild count

    try:
        with open("guilds.json", "r") as f:
            json.load(f)
    except FileNotFoundError:
        with open("guilds.json", "w") as f:
            json.dump({}, f)

    async with client:
        try:
            import topgg  # type: ignore

            dbl_token = config.DBL.TOKEN
            client.topggpy = topgg.DBLClient(
                client, dbl_token, autopost=True, post_shard_count=True
            )
            client.topgg_webhook = topgg.WebhookManager(client).dbl_webhook(
                "/dbl", config.DBL.WEBHOOK_PASSWORD
            )
            client.topgg_webhook.run(config.DBL.WEBHOOK_PORT)
        except ImportError:
            print("Top.gg integration not found.")

        # Adding Extensions

        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded extension: {filename[:-3]}")

        await client.start(config.BOT_TOKEN)


if __name__ == "__main__":

    asyncio.run(main())
