import discord, json, os, redis, topgg
from discord.ext import commands
import logging

with open("Data/config.json", "r") as f:
    config = json.load(f)

default_linked = {
    "voice": {},
    "stage": {},
    "category": {},
    "all": {"roles": [], "except": []},
    "permanent": {},
}
default_gdata = {"tts": {"enabled": False, "role": None}, "logging": None}

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


class RedisUtils:
    """Tools for interacting with the Redis database & converting datatypes"""

    def __init__(self, r: redis.Redis):
        self.r = r

    def list_to_str(self, l: list) -> str:
        return json.dumps(l)

    def str_to_list(self, s: str) -> list:
        return json.loads(s)

    def dict_to_str(self, d: dict) -> str:
        return json.dumps(d)

    def str_to_dict(self, s: bytes) -> dict:
        return json.loads(s.decode("utf-8"))

    def str_to_bool(self, s: bytes) -> bool:
        if s.decode("utf-8") == True:
            return True
        return False

    def decode(self, s: bytes) -> str:
        return s.decode("utf-8")

    def guild_add(self, guild_id: int, type = None):
        if type == None:
            # Guild data
            self.r.hset(f"{guild_id}:gd", "tts:enabled", "False")
            self.r.hset(f"{guild_id}:gd", "tts:role", "None")
            self.r.hset(f"{guild_id}:gd", "logging", "None")

            # Linked data
            self.r.hset(f"{guild_id}:linked", "voice", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "stage", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "category", self.dict_to_str({}))
            self.r.hset(
                f"{guild_id}:linked", "all", self.dict_to_str({"roles": [], "except": []})
            )
            self.r.hset(f"{guild_id}:linked", "permanent", self.dict_to_str({}))

            # Generator data
            self.r.hset(f"{guild_id}:gen", "cat", "0")
            self.r.hset(f"{guild_id}:gen", "gen_id", "0")
            self.r.hset(f"{guild_id}:gen", "open", self.list_to_str([]))
        elif type == 'gen':
            # Generator data
            self.r.hset(f"{guild_id}:gen", "cat", "0")
            self.r.hset(f"{guild_id}:gen", "gen_id", "0")
            self.r.hset(f"{guild_id}:gen", "open", self.list_to_str([]))
        elif type == 'gd':
            # Guild data
            self.r.hset(f"{guild_id}:gd", "tts:enabled", "False")
            self.r.hset(f"{guild_id}:gd", "tts:role", "None")
            self.r.hset(f"{guild_id}:gd", "logging", "None")
        elif type == 'linked':
            # Linked data
            self.r.hset(f"{guild_id}:linked", "voice", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "stage", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "category", self.dict_to_str({}))
            self.r.hset(
                f"{guild_id}:linked", "all", self.dict_to_str({"roles": [], "except": []})
            )
            self.r.hset(f"{guild_id}:linked", "permanent", self.dict_to_str({}))

        return True

    def guild_remove(self, guild_id: int):
        self.r.delete(f"{guild_id}:gd", f"{guild_id}:linked", f"{guild_id}:gen")

    def get_guild_data(self, guild_id: int) -> dict:
        r_data = self.r.hgetall(f"{guild_id}:gd")
        if r_data:
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data
        else:
            self.guild_add(guild_id, 'gd')
            r_data = self.r.hgetall(f"{guild_id}:gd")
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data


    def update_guild_data(self, guild_id: int, data: dict):
        for key in data:
            self.r.hset(f"{guild_id}:gd", key, data[key])

    def get_linked(self, type: str, guild_id: int) -> dict:
        r_data = self.r.hget(f"{guild_id}:linked", type)
        if r_data:
            return self.str_to_dict(r_data)
        else:
            self.guild_add(guild_id, 'linked')
            r_data = self.r.hget(f"{guild_id}:linked", type)
            return self.str_to_dict(r_data)

    def update_linked(self, type: str, guild_id: int, data: dict):
        self.r.hset(f"{guild_id}:linked", type, self.dict_to_str(data))

    def get_generator(self, guild_id: int) -> dict:
        r_data = self.r.hgetall(f"{guild_id}:gen")
        if r_data:
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data
        else:
            self.guild_add(guild_id, 'gen')

            r_data = self.r.hgetall(f"{guild_id}:gen")
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data

    def update_generator(self, guild_id: int, data: dict):
        for key in data:
            if key == "open":
                self.r.hset(f"{guild_id}:gen", key, self.list_to_str(data[key]))
            else:
                self.r.hset(f"{guild_id}:gen", key, data[key])


class MyClient(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        r = redis.Redis(
            host="172.18.0.1", port=6379, db=0, password="sht8RNp@@X5CoEy&"
        )
        self.redis = RedisUtils(r)

    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds.")
        print("------")

        await client.change_presence(status=discord.Status.online)
        await client.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="Voice Channels"
            )
        )

    async def on_guild_join(self, guild: discord.Guild):
        self.redis.guild_add(guild.id)

    async def on_guild_remove(self, guild: discord.Guild):
        self.redis.guild_remove(guild.id)

    async def on_application_command_error(self, ctx, error):

        if isinstance(error, commands.MissingPermissions):
            await ctx.respond(
                "You do not have the required permissions to use this command."
            )

        if isinstance(error, commands.NotOwner):
            await ctx.respond("This is a developer only command.")

        else:
            try:
                await ctx.respond(f"Error: {error}")
            except:
                pass


intents = discord.Intents(messages=True, guilds=True, reactions=True, voice_states=True)

client = MyClient("VCROLESDONOTUSE", intents=intents)

dbl_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6Ijc3NTAyNTc5NzAzNDU0MTEwNyIsImJvdCI6dHJ1ZSwiaWF0IjoxNjA2MDYyNTE5fQ.gGilud7TbOEFJP5aGJ1TeYaWN48n6ohpHOKIdoUFB3E"
client.topggpy = topgg.DBLClient(client, dbl_token, autopost=True, post_shard_count=True)

@client.event
async def on_autopost_success():
    print(
        f"Posted server count ({client.topggpy.guild_count}), shard count ({client.shard_count})"
    )

# COMMANDS

# DEV Commands
@client.slash_command(
    description="DEVELOPER COMMAND", guild_ids=config["MANAGE_GUILD_IDS"]
)
@commands.is_owner()
async def load(ctx: discord.ApplicationContext, extension: str):
    try:
        client.load_extension(f"cogs.{extension}")
        await ctx.respond(f"Successfully loaded {extension}")
    except:
        await ctx.respond(f"Failed while loading {extension}")


@client.slash_command(
    description="DEVELOPER COMMAND", guild_ids=config["MANAGE_GUILD_IDS"]
)
@commands.is_owner()
async def unload(ctx: discord.ApplicationContext, extension: str):
    try:
        client.unload_extension(f"cogs.{extension}")
        await ctx.respond(f"Successfully unloaded {extension}")
    except:
        await ctx.respond(f"Failed while unloading {extension}")


@client.slash_command(
    description="DEVELOPER COMMAND", guild_ids=config["MANAGE_GUILD_IDS"]
)
@commands.is_owner()
async def reload(ctx: discord.ApplicationContext, extension: str):
    try:
        client.reload_extension(f"cogs.{extension}")
        await ctx.respond(f"Successfully reloaded {extension}")
    except:
        await ctx.respond(f"Failed while reloading {extension}")


@client.slash_command(
    description="DEVELOPER COMMAND", guild_ids=config["MANAGE_GUILD_IDS"]
)
@commands.is_owner()
async def logs(
    ctx: discord.ApplicationContext,
):  # , type: Option(str, 'Log type', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'])):
    await ctx.respond("Fetching Logs...")
    await ctx.channel.send(file=discord.File(f"discord.log"))


if __name__ == "__main__":

    # Adding Extensions

    for filename in os.listdir("cogs"):
        if filename.endswith(".py"):
            client.load_extension(f"cogs.{filename[:-3]}")
            print(f"Loaded extension: {filename[:-3]}")

    # Removing TTS files

    for filename in os.listdir("tts"):
        if filename.endswith(".mp3"):
            os.remove(f"tts\\{filename}")

    # Running the bot.

    client.run(config["BOT_TOKEN"])
