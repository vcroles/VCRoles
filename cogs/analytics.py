import datetime as dt
import io
import json

import discord
from discord import Interaction, app_commands
from discord.ext import commands, tasks

from utils.client import VCRolesClient


class Analytics(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.time_spent_loop.start()

    async def cog_unload(self):
        self.time_spent_loop.cancel()

        return await super().cog_unload()

    analytic_commands = app_commands.Group(
        name="analytics", description="Use to enable or disable analytics"
    )

    @analytic_commands.command(name="toggle")
    @app_commands.describe(
        channel="Channel to send analytics to:",
        enable="Enable analytics:",
    )
    async def toggle_analytics(
        self, interaction: Interaction, enable: bool, channel: discord.TextChannel
    ):
        """PREMIUM - Use to toggle analytics"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        guild = await self.client.db.get_guild_data(interaction.guild.id)

        if not guild.premium:
            embed = discord.Embed(
                title="Premium Required",
                description="Sorry, you cannot enable analytics in this server - consider upgrading to premium to unlock this. https://cde90.gumroad.com/l/vcroles",
                colour=discord.Colour.red(),
            )
            return await interaction.response.send_message(embed=embed)

        if enable:
            await self.client.db.update_guild_data(
                interaction.guild.id, analytics=str(channel.id)
            )
            embed = discord.Embed(
                title="Analytics Enabled",
                description=f"Analytics have been enabled in {channel.mention}",
                colour=discord.Colour.green(),
            )
            return await interaction.response.send_message(embed=embed)

        await self.client.db.update_guild_data(interaction.guild.id, analytics=None)
        embed = discord.Embed(
            title="Analytics Disabled",
            description="Analytics have been disabled",
            colour=discord.Colour.green(),
        )
        return await interaction.response.send_message(embed=embed)

    @tasks.loop(minutes=1)
    async def time_spent_loop(self):
        guilds = await self.client.db.get_analytic_guilds()

        for guild in guilds:
            if not guild.analytics:
                continue

            # loop through every voice channel in the guild
            # for each channel, get the number of members in it
            # add the total number of members in voice channels
            # to the redis database for hash guild:id:analytics -> voice_minutes
            g = self.client.get_guild(int(guild.id))
            if not g:
                continue
            total = 0
            for channel in g.voice_channels:
                total += len(channel.members)

            await self.client.ar.hincrby(
                f"guild:{guild.id}:analytics", "voice_minutes", total
            )

    @time_spent_loop.before_loop
    async def before_time_spent_loop(self):
        await self.client.wait_until_ready()

    async def get_analytic_embed(self, guild: str) -> discord.Embed:
        analytics = await self.client.ar.hgetall(f"guild:{guild}:analytics")

        embed = discord.Embed(
            title="VC Roles Analytics",
            description="Here are your analytics for the last 24 hours",
            colour=discord.Colour.green(),
        )

        embed.add_field(
            name="Voice Minutes",
            value=analytics.get("voice_minutes", 0),
            inline=False,
        )

        embed.add_field(
            name="Voice Channels Joined / Left / Changed",
            value=f"{analytics.get('voice_channel_joins', 0)} / {analytics.get('voice_channel_leaves', 0)} / {analytics.get('voice_channel_changes', 0)}",
            inline=False,
        )

        embed.add_field(
            name="Roles Added / Removed",
            value=f"{analytics.get('roles_added', 0)} / {analytics.get('roles_removed', 0)}",
            inline=False,
        )

        embed.add_field(
            name="Commands Used",
            value=analytics.get("commands_used", 0),
            inline=False,
        )

        embed.add_field(
            name="Generated Voice Channels",
            value=analytics.get("generated_voice_channels", 0),
            inline=False,
        )

        embed.add_field(
            name="TTS Messages Sent",
            value=analytics.get("tts_messages_sent", 0),
            inline=False,
        )

        return embed

    @tasks.loop(time=dt.time(hour=0, minute=0))
    async def analytics_loop(self):
        guilds = await self.client.db.get_analytic_guilds()

        for guild in guilds:
            if not guild.analytics:
                continue

            g = self.client.get_guild(int(guild.id))
            if not g:
                continue

            channel = g.get_channel(int(guild.analytics))
            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            embed = await self.get_analytic_embed(guild.id)

            await channel.send(embed=embed)

            await self.client.ar.rename(  # type: ignore
                f"guild:{guild.id}:analytics",
                f"guild:{guild.id}:analytics:{dt.datetime.utcnow().strftime('%Y-%m-%d')}",
            )
            # set the new hash to expire in 30 days
            await self.client.ar.expire(
                f"guild:{guild.id}:analytics:{dt.datetime.utcnow().strftime('%Y-%m-%d')}",
                30 * 24 * 60 * 60,
            )

    @analytics_loop.before_loop
    async def before_analytics_loop(self):
        await self.client.wait_until_ready()

    @analytic_commands.command(name="view")
    async def view_analytics(self, interaction: Interaction):
        """PREMIUM - Use to view analytics"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        guild = await self.client.db.get_guild_data(interaction.guild.id)

        if not guild.premium:
            embed = discord.Embed(
                title="Premium Required",
                description="Sorry, you cannot view analytics in this server - consider upgrading to premium to unlock this. https://cde90.gumroad.com/l/vcroles",
                colour=discord.Colour.red(),
            )
            return await interaction.response.send_message(embed=embed)

        embed = await self.get_analytic_embed(guild.id)

        return await interaction.response.send_message(embed=embed)

    @analytic_commands.command(name="export")
    async def export_analytics(self, interaction: Interaction):
        """PREMIUM - Export past 30 days of analytics"""
        if not interaction.guild:
            return await interaction.response.send_message(
                "This command can only be used in a server"
            )

        guild = await self.client.db.get_guild_data(interaction.guild.id)

        if not guild.premium:
            embed = discord.Embed(
                title="Premium Required",
                description="Sorry, you cannot export analytics in this server - consider upgrading to premium to unlock this. https://cde90.gumroad.com/l/vcroles",
                colour=discord.Colour.red(),
            )
            return await interaction.response.send_message(embed=embed)

        analytics = await self.client.ar.keys(f"guild:{guild.id}:analytics:*")

        if not analytics:
            embed = discord.Embed(
                title="No Analytics Found",
                description="Sorry, there are no analytics to export",
                colour=discord.Colour.red(),
            )
            return await interaction.response.send_message(embed=embed)

        analytics = await self.client.ar.mget(*analytics)

        analytics = [json.loads(a) for a in analytics]

        analytics = {k: sum(d[k] for d in analytics) for k in analytics[0]}

        analytics = json.dumps(analytics)

        analytics = io.BytesIO(analytics.encode("utf-8"))

        analytics.seek(0)

        return await interaction.response.send_message(
            "Here is your analytics export",
            file=discord.File(analytics, filename="analytics.json"),
        )


async def setup(client: VCRolesClient):
    await client.add_cog(Analytics(client))
