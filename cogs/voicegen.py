import discord
from discord.commands import Option
from discord.ext import commands
from bot import MyClient


class VoiceGen(commands.Cog):
    def __init__(self, client: MyClient):
        self.client = client

    @commands.slash_command(description="A command to create a voice channel generator")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def voicegenerator(
        self,
        ctx: discord.ApplicationContext,
        category_name: Option(
            str, "Name of generator category", required=False, default="Voice Generator"
        ),
        voice_channel_name: Option(
            str,
            "Voice generator channel name",
            required=False,
            default="Voice Generator",
        ),
        interface_channel_name: Option(
            str,
            "Interface channel name",
            required=False,
            default="VC Roles Interface",
        ),
    ):
        data = self.client.redis.get_generator(ctx.guild.id)

        category = await ctx.guild.create_category(name=category_name)

        voice_channel = await ctx.guild.create_voice_channel(
            name=voice_channel_name, category=category
        )

        interface_channel = await ctx.guild.create_text_channel(
            name=interface_channel_name, category=category
        )

        creation_embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Setup**",
            description=f"The category **{category.name}**, voice channel **{voice_channel.name}**, and interface channel {interface_channel.mention} have been created.\n Join the voice channel to generate a voice channel.",
        )
        await ctx.respond(embed=creation_embed)

        interface_options = [
            ":lock: Locks your VC so no one can join it.",
            ":unlock: Unlocks your VC so people can join it.",
            ":no_entry_sign: Hides your VC so no one can see it.",
            ":eye: Unhide your VC so people can see it.",
            ":heavy_plus_sign: Increases the user limit of your VC.",
            ":heavy_minus_sign: Decreases the user limit of your VC.",
        ]

        emoji_list = [
            "🔒",
            "🔓",
            "🚫",
            "👁",
            "➕",
            "➖",
        ]

        description_str = "\n".join(interface_options)

        interface_embed = discord.Embed(
            title="Voice Generator Interface",
            description=f"You can use this interface to customize your private voice channel.\n\n{description_str}",
            color=discord.Color.blue(),
        )
        interface_embed.set_thumbnail(url=self.client.user.avatar.url)
        interface_embed.set_footer(text="Use these commands via the reactions below.")

        interface_message = await interface_channel.send(embed=interface_embed)

        data = {
            "cat": str(category.id),
            "gen_id": str(voice_channel.id),
            "open": [],
            "interface": {
                "channel": str(interface_channel.id),
                "msg_id": str(interface_message.id),
            },
        }

        self.client.redis.update_generator(ctx.guild.id, data)

        [await interface_message.add_reaction(emoji) for emoji in emoji_list]

    @commands.slash_command(description="A command to remove a voice channel generator")
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def removegenerator(self, ctx: discord.ApplicationContext):

        self.client.redis.r.delete(f"{ctx.guild.id}:gen")

        embed = discord.Embed(
            color=discord.Color.green(),
            title="**Voice Generator Removal**",
            description=f"The channel will now no longer act as a voice channel generator",
        )
        await ctx.respond(embed=embed)


def setup(client):
    client.add_cog(VoiceGen(client))
