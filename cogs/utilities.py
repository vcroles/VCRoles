import discord
from discord.ext import commands
from bot import MyClient


class Utils(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description="Gets an invite to the support server")
    async def discord(self, ctx: discord.ApplicationContext):
        await ctx.respond("https://discord.gg/yHU6qcgNPy")

    @commands.slash_command(description="Gets an invite for the bot")
    async def invite(self, ctx):
        await ctx.respond(
            "https://discord.com/api/oauth2/authorize?client_id=775025797034541107&permissions=300944400&scope=bot%20applications.commands"
        )

    @commands.slash_command(description="Gets info about the bot")
    async def about(self, ctx):
        embed = discord.Embed(title="About:", colour=discord.Colour.blue())

        embed.add_field(
            name="__**Server Count**__",
            value=f"VC Roles is in {len(self.client.guilds)} servers",
            inline=False,
        )
        embed.add_field(
            name="__**Current Bot Version**__", value="Bot Version - 2.0", inline=False
        )
        shard_id = ctx.guild.shard_id
        embed.add_field(
            name="__**Shard Info**__",
            value=f"Shard {shard_id+1}/{len(self.client.shards)}",
        )

        embed.add_field(
            name="__**Authors**__",
            value=f"**cde#4572** and **SamHartland#9376**",
            inline=False,
        )
        embed.set_author(
            name=f"{self.client.user}", icon_url=self.client.user.avatar.url
        )

        await ctx.respond(embed=embed)

    @commands.slash_command(description="Help Command")
    async def help(self, ctx):
        embed = discord.Embed(
            title="VC Roles Help",
            description="We have moved our help page to https://www.vcroles.com where you can find a list of the bot's commands, how to use them, a basic setup guide and more!",
            colour=discord.Colour.light_grey(),
        )
        embed.set_footer(text="https://www.vcroles.com")
        await ctx.respond(embed=embed)


def setup(client: MyClient):
    client.add_cog(Utils(client))
