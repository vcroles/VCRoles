import csv
import datetime as dt
import io
from typing import Literal

import matplotlib

matplotlib.use("Agg")

import discord
import matplotlib.dates as mdates
from discord import Interaction, app_commands
from discord.ext import commands, tasks
from matplotlib.figure import Figure

from utils.client import VCRolesClient


class Analytics(commands.Cog):
    def __init__(self, client: VCRolesClient):
        self.client = client
        self.time_spent_loop.start()
        self.analytics_loop.start()

    async def cog_unload(self):
        self.time_spent_loop.cancel()
        self.analytics_loop.cancel()

        return await super().cog_unload()

    analytic_commands = app_commands.Group(
        name="analytics", description="Use to enable or disable analytics"
    )

    @analytic_commands.command(name="toggle")
    @app_commands.describe(
        enable="Enable analytics:",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def toggle_analytics(self, interaction: Interaction, enable: bool):
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
            embed = discord.Embed(
                title="Analytics Enabled",
                description="Analytics have been enabled. To view your analytics, use `/analytics graph`, `/analytics view` or `/analytics export`.\nTo disable analytics, use `/analytics toggle false`",
                colour=discord.Colour.green(),
            )
            await self.client.db.update_guild_data(interaction.guild.id, analytics=True)
            return await interaction.response.send_message(embed=embed)

        await self.client.db.update_guild_data(interaction.guild.id, analytics=False)
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

            if total == 0:
                continue

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
    @app_commands.checks.has_permissions(administrator=True)
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

        if not guild.analytics:
            embed = discord.Embed(
                title="Analytics Disabled",
                description="Analytics have been disabled. Use `/analytics toggle` to enable them",
                colour=discord.Colour.green(),
            )
            return await interaction.response.send_message(embed=embed)

        embed = await self.get_analytic_embed(guild.id)

        return await interaction.response.send_message(embed=embed)

    @analytic_commands.command(name="export")
    @app_commands.checks.has_permissions(administrator=True)
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

        # create a csv file as a buffer
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # write the header
        writer.writerow(
            [
                "date",
                "voice_minutes",
                "voice_channel_joins",
                "voice_channel_leaves",
                "voice_channel_changes",
                "roles_added",
                "roles_removed",
                "commands_used",
                "generated_voice_channels",
                "tts_messages_sent",
            ]
        )

        for analytic in analytics:
            date = analytic.split(":")[-1]
            analytic = await self.client.ar.hgetall(analytic)
            writer.writerow(
                [
                    date,
                    analytic.get("voice_minutes", 0),
                    analytic.get("voice_channel_joins", 0),
                    analytic.get("voice_channel_leaves", 0),
                    analytic.get("voice_channel_changes", 0),
                    analytic.get("roles_added", 0),
                    analytic.get("roles_removed", 0),
                    analytic.get("commands_used", 0),
                    analytic.get("generated_voice_channels", 0),
                    analytic.get("tts_messages_sent", 0),
                ]
            )

        buffer.seek(0)

        await interaction.response.send_message(
            "Here is your analytics export", file=discord.File(buffer, "analytics.csv")  # type: ignore
        )

    @analytic_commands.command(name="graph")
    @app_commands.checks.has_permissions(administrator=True)
    async def graph_analytics(
        self, interaction: Interaction, timeframe: Literal["hour", "day"] = "hour"
    ):
        """PREMIUM - Create a graph of hourly/daily analytics"""
        await interaction.response.defer()

        if not interaction.guild:
            return await interaction.followup.send(
                "This command can only be used in a server"
            )

        guild = await self.client.db.get_guild_data(interaction.guild.id)

        if not guild.premium:
            embed = discord.Embed(
                title="Premium Required",
                description="Sorry, you cannot view analytics in this server - consider upgrading to premium to unlock this. https://cde90.gumroad.com/l/vcroles",
                colour=discord.Colour.red(),
            )
            return await interaction.followup.send(embed=embed)

        if not guild.analytics:
            embed = discord.Embed(
                title="Analytics Disabled",
                description="Analytics have been disabled. Use `/analytics toggle` to enable them",
                colour=discord.Colour.green(),
            )
            return await interaction.followup.send(embed=embed)

        if timeframe == "hour":
            analytics = await self.client.ar.hgetall(f"guild:{guild.id}:analytics")
            if not analytics:
                embed = discord.Embed(
                    title="No Analytics Found",
                    description="Sorry, there are no analytics to graph",
                    colour=discord.Colour.red(),
                )
                return await interaction.followup.send(embed=embed)

            hourly_voice_minutes: list[int] = []
            hourly_voice_channel_joins: list[int] = []
            hourly_voice_channel_leaves: list[int] = []
            hourly_voice_channel_changes: list[int] = []
            hourly_roles_added: list[int] = []
            hourly_roles_removed: list[int] = []
            hourly_commands_used: list[int] = []
            hourly_generated_voice_channels: list[int] = []
            hourly_tts_messages_sent: list[int] = []

            for i in range(24):
                hourly_voice_minutes.append(int(analytics.get(f"voice_minutes-{i}", 0)))
                hourly_voice_channel_joins.append(
                    int(analytics.get(f"voice_channel_joins-{i}", 0))
                )
                hourly_voice_channel_leaves.append(
                    int(analytics.get(f"voice_channel_leaves-{i}", 0))
                )
                hourly_voice_channel_changes.append(
                    int(analytics.get(f"voice_channel_changes-{i}", 0))
                )
                hourly_roles_added.append(int(analytics.get(f"roles_added-{i}", 0)))
                hourly_roles_removed.append(int(analytics.get(f"roles_removed-{i}", 0)))
                hourly_commands_used.append(int(analytics.get(f"commands_used-{i}", 0)))
                hourly_generated_voice_channels.append(
                    int(analytics.get(f"generated_voice_channels-{i}", 0))
                )
                hourly_tts_messages_sent.append(
                    int(analytics.get(f"tts_messages_sent-{i}", 0))
                )

            def get_figure_hourly() -> Figure:
                fig = Figure()
                ax = fig.subplots()  # type: ignore

                ax.plot(hourly_voice_minutes, label="Voice Minutes")  # type: ignore
                ax.plot(hourly_voice_channel_joins, label="Voice Channel Joins")  # type: ignore
                ax.plot(hourly_voice_channel_leaves, label="Voice Channel Leaves")  # type: ignore
                ax.plot(hourly_voice_channel_changes, label="Voice Channel Changes")  # type: ignore
                ax.plot(hourly_roles_added, label="Roles Added")  # type: ignore
                ax.plot(hourly_roles_removed, label="Roles Removed")  # type: ignore
                ax.plot(hourly_commands_used, label="Commands Used")  # type: ignore
                ax.plot(  # type: ignore
                    hourly_generated_voice_channels, label="Generated Voice Channels"
                )
                ax.plot(hourly_tts_messages_sent, label="TTS Messages Sent")  # type: ignore

                ax.set_xlabel("Hour")  # type: ignore
                ax.set_xticks(range(0, 24, 3))  # type: ignore
                ax.set_ylabel("Count")  # type: ignore
                ax.set_title("Hourly Analytics")  # type: ignore

                ax.legend()  # type: ignore

                return fig

            fig = await self.client.loop.run_in_executor(None, get_figure_hourly)

            buffer = io.BytesIO()
            fig.savefig(buffer, format="png")  # type: ignore

            buffer.seek(0)

            await interaction.followup.send(
                "Here is your analytics graph",
                file=discord.File(buffer, "analytics.png"),
            )

        elif timeframe == "day":
            analytic_days = await self.client.ar.keys(f"guild:{guild.id}:analytics:*")

            if not analytic_days:
                embed = discord.Embed(
                    title="No Analytics Found",
                    description="Sorry, there are not enough analytics to graph",
                    colour=discord.Colour.red(),
                )
                return await interaction.followup.send(embed=embed)

            analytic_days.sort()
            analytic_days.append(f"guild:{guild.id}:analytics")

            daily_voice_minutes: list[int] = []
            daily_voice_channel_joins: list[int] = []
            daily_voice_channel_leaves: list[int] = []
            daily_voice_channel_changes: list[int] = []
            daily_roles_added: list[int] = []
            daily_roles_removed: list[int] = []
            daily_commands_used: list[int] = []
            daily_generated_voice_channels: list[int] = []
            daily_tts_messages_sent: list[int] = []

            dates: list[dt._Date] = []  # type: ignore

            for day in analytic_days:
                data = await self.client.ar.hgetall(day)

                date = day.split(":")[-1]
                if date == "analytics":
                    date = dt.datetime.utcnow().strftime("%Y-%m-%d")
                dates.append(dt.datetime.strptime(date, "%Y-%m-%d").date())

                daily_voice_minutes.append(int(data.get("voice_minutes", 0)))
                daily_voice_channel_joins.append(
                    int(data.get("voice_channel_joins", 0))
                )
                daily_voice_channel_leaves.append(
                    int(data.get("voice_channel_leaves", 0))
                )
                daily_voice_channel_changes.append(
                    int(data.get("voice_channel_changes", 0))
                )
                daily_roles_added.append(int(data.get("roles_added", 0)))
                daily_roles_removed.append(int(data.get("roles_removed", 0)))
                daily_commands_used.append(int(data.get("commands_used", 0)))
                daily_generated_voice_channels.append(
                    int(data.get("generated_voice_channels", 0))
                )
                daily_tts_messages_sent.append(int(data.get("tts_messages_sent", 0)))

            def get_figure_daily() -> Figure:
                fig = Figure()
                ax = fig.subplots()  # type: ignore

                ax.plot(dates, daily_voice_minutes, label="Voice Minutes")  # type: ignore
                ax.plot(dates, daily_voice_channel_joins, label="Voice Channel Joins")  # type: ignore
                ax.plot(dates, daily_voice_channel_leaves, label="Voice Channel Leaves")  # type: ignore
                ax.plot(  # type: ignore
                    dates, daily_voice_channel_changes, label="Voice Channel Changes"
                )
                ax.plot(dates, daily_roles_added, label="Roles Added")  # type: ignore
                ax.plot(dates, daily_roles_removed, label="Roles Removed")  # type: ignore
                ax.plot(dates, daily_commands_used, label="Commands Used")  # type: ignore
                ax.plot(  # type: ignore
                    dates,
                    daily_generated_voice_channels,
                    label="Generated Voice Channels",
                )
                ax.plot(dates, daily_tts_messages_sent, label="TTS Messages Sent")  # type: ignore

                ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%y"))  # type: ignore
                interval = len(dates) // 5
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))  # type: ignore
                ax.set_xlabel("Day")  # type: ignore
                ax.set_ylabel("Count")  # type: ignore
                ax.set_title("Daily Analytics")  # type: ignore

                ax.legend()  # type: ignore

                return fig

            fig = await self.client.loop.run_in_executor(None, get_figure_daily)

            buffer = io.BytesIO()
            fig.savefig(buffer, format="png")  # type: ignore

            buffer.seek(0)

            await interaction.followup.send(
                "Here is your analytics graph",
                file=discord.File(buffer, "analytics.png"),
            )


async def setup(client: VCRolesClient):
    await client.add_cog(Analytics(client))
