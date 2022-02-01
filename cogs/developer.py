import discord, json
from discord.commands import Option
from discord import ApplicationContext
from discord.ext import commands
from bot import MyClient

with open("Data/config.json", "r") as f:
    config = json.load(f)


class Dev(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def change_status(self, ctx, status=None, *, message: str = None):
        try:
            status = int(status)
        except:
            pass

        if status == 1:
            status_embed = discord.Embed(
                colour=discord.Color.blue(),
                title="__**Success**__",
                description=f"Activity Type set to listening\nMessage set to {message}",
            )
            await self.client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, name=message
                )
            )
            await ctx.send(embed=status_embed)
        elif status == 2:
            status_embed = discord.Embed(
                colour=discord.Color.blue(),
                title="__**Success**__",
                description=f"Activity Type set to Watching\nMessage set to {message}",
            )
            await self.client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.watching, name=message
                )
            )
            await ctx.send(embed=status_embed)
        elif status == 3:
            status_embed = discord.Embed(
                colour=discord.Color.blue(),
                title="__**Success**__",
                description=f"Activity Type set to Playing\nMessage set to {message}",
            )
            await self.client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.playing, name=message
                )
            )
            await ctx.send(embed=status_embed)
        elif status == None:
            status_embed = discord.Embed(
                colour=discord.Color.blue(),
                title="__**Numbers For Status Changing**__",
                description="Listening - 1 \nWatching - 2\nPlaying - 3\n Plain Genric one - 4",
            )
            await ctx.send(embed=status_embed)
        elif status == 4:
            status_embed = discord.Embed(
                colour=discord.Color.blue(),
                title="__**Success**__",
                description="Activity Type set to Listening\nMessage set to /help - www.vcroles.com",
            )
            await self.client.change_presence(
                activity=discord.Activity(
                    type=discord.ActivityType.listening, name="/help - www.vcroles.com"
                )
            )
            await ctx.send(embed=status_embed)

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def servernum(self, ctx):
        await ctx.send(f"Bot is in {len(self.client.guilds)} servers")

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def shards(self, ctx):
        shard_embed = discord.Embed(
            colour=discord.Colour.blue(),
            title="Sharding Info:",
            description=f"There are {len(self.client.shards)} shards.\nThis is shard {ctx.guild.shard_id} - latency: {round(self.client.latency * 1000)} ms",
        )
        await ctx.send(embed=shard_embed)

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def coglist(self, ctx):
        await ctx.send(f"The cogs are:\n{self.client.cogs.keys()}")

    @commands.command(description="DEVELOPER COMMAND")
    @commands.is_owner()
    async def remind(self, ctx):
        await self.client.send_reminder()
        await ctx.send("Reminder sent")


def setup(client):
    client.add_cog(Dev(client))
