import discord
from discord.commands import Option
from discord.ext import commands
from bot import MyClient


class voicegen(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description="A command to create a voice channel generator")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def voicegenerator(
        self,
        ctx: discord.ApplicationContext,
        category: Option(
            str, "Name of generator category", required=False, default="Voice Generator"
        ),
        channel: Option(
            str,
            "Voice generator channel name",
            required=False,
            default="Voice Generator",
        ),
    ):
        data = self.client.redis.get_generator(ctx.guild.id)

        category = await ctx.guild.create_category(name=category)

        channel = await ctx.guild.create_voice_channel(name=channel, category=category)

        data = {
            "cat": str(category.id),
            "gen_id": str(channel.id),
            "open": self.client.redis.list_to_str([]),
        }

        self.client.redis.update_generator(ctx.guild.id, data)

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Setup**",
            description=f"The category **{category.name}** and voice channel **{channel.name}** have been created.\n Join the voice channel to generate a voice channel.",
        )
        await ctx.respond(embed=creation_embed)

    @commands.slash_command(description="A command to remove a voice channel generator")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def removegenerator(self, ctx: discord.ApplicationContext):
        data = self.client.redis.get_generator(ctx.guild.id)

        self.client.redis.r.hset(f"{ctx.guild_id}:gen", "cat", "0")
        self.client.redis.r.hset(f"{ctx.guild_id}:gen", "gen_id", "0")
        self.client.redis.r.hset(
            f"{ctx.guild_id}:gen", "open", self.client.redis.list_to_str([])
        )

        self.client.redis.update_generator(ctx.guild.id, data)

        embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Removal**",
            description=f"The channel will now no longer act as a voice channel generator",
        )
        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(voicegen(client))
