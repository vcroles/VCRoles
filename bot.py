from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import discord
import redis.asyncio as aioredis
from discord import app_commands

import config
from utils.client import VCRolesClient
from utils.database import DatabaseUtils
from utils.logging import setup_logging
from utils.types import using_topgg
from views.url import TopGG

setup_logging()

intents = discord.Intents(messages=True, guilds=True, reactions=True, voice_states=True)

ar: aioredis.Redis[Any] = aioredis.Redis(
    host=config.REDIS.HOST,
    password=config.REDIS.PASSWORD,
    port=config.REDIS.PORT,
    db=config.REDIS.DB,
    decode_responses=True,
)
db_utils = DatabaseUtils()

client = VCRolesClient(ar, intents=intents, db=db_utils)
client.remove_command("help")


if using_topgg:
    import topgg

    @client.event
    async def on_autopost_success():
        with open("guilds.log", "a") as file:
            file.write(
                f"{discord.utils.utcnow().strftime('%d/%m/%Y, %H:%M:%S')}: Posted server count ({len(client.guilds)}), shard count ({client.shard_count})\n"
            )

    @client.event
    async def on_dbl_vote(data: topgg.types.BotVoteData):
        if data.type == "upvote":
            client.loop.create_task(client.ar.hset("commands", str(data.user), -10_000))

            try:
                user = await client.fetch_user(data.user)
                description = f"{user.mention} ({user.name}) just voted for VC Roles on Top.gg & received unlimited command usage for the rest of the day!\n\nClick [here](https://top.gg/bot/775025797034541107/vote) to vote"
            except:
                user = discord.Object(id=int(data.user))
                description = f"<@{user.id}> just voted for VC Roles on Top.gg & received unlimited command usage for the rest of the day!\n\nClick [here](https://top.gg/bot/775025797034541107/vote) to vote"

            channel = client.get_channel(947070091797856276)
            if not isinstance(channel, discord.TextChannel):
                raise AssertionError
            embed = discord.Embed(
                colour=discord.Colour.blue(),
                title=":tada: Top.gg Vote! :tada:",
                description=description,
                url="https://top.gg/bot/775025797034541107/vote",
            )
            if isinstance(user, discord.Member | discord.User):
                embed.set_thumbnail(
                    url=user.avatar.url
                    if user.avatar
                    else client.user.avatar.url
                    if client.user and client.user.avatar
                    else None
                )
            embed.set_footer(text="Thanks for voting!")
            await channel.send(embed=embed)
        else:
            print(data)

    @topgg.endpoint("/dbl", topgg.WebhookType.BOT, config.DBL.WEBHOOK_PASSWORD)
    def dbl_endpoint(
        vote_data: topgg.types.BotVoteData,
        _client: VCRolesClient = topgg.data(VCRolesClient),
    ):
        client.dispatch("dbl_vote", vote_data)


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
    if isinstance(error, app_commands.BotMissingPermissions):
        return await interaction.response.send_message(
            error,
            ephemeral=True,
        )
    if isinstance(error, app_commands.CheckFailure):
        embed = discord.Embed(
            title="Command Limit Reached",
            description="You have reached your command limit for today, but **don't worry!** You can get **unlimited** command usage for the rest of the day by [voting for the bot on Top.gg!](https://top.gg/bot/775025797034541107/vote)",
            colour=discord.Colour.brand_red(),
            url="https://top.gg/bot/775025797034541107/vote",
        )
        embed.set_thumbnail(
            url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        if client.user and client.user.avatar:
            embed.set_author(name=client.user.name, icon_url=client.user.avatar.url)
        embed.set_footer(text="Thanks for using the bot!")

        return await interaction.response.send_message(
            embed=embed, ephemeral=True, view=TopGG()
        )
    else:
        return


async def main():

    # Removing Export Files

    for filename in os.listdir("exports"):
        if filename.endswith(".json"):
            os.remove(f"exports/{filename}")

    # Removing TTS Files

    for filename in os.listdir("tts"):
        if filename.endswith(".mp3"):
            os.remove(f"tts/{filename}")

    # Setting up guild count file

    try:
        with open("guilds.json", "r") as f:
            json.load(f)
    except FileNotFoundError:
        with open("guilds.json", "w") as f:
            json.dump({}, f)

    async with client:

        # Setting up topgg integration

        if using_topgg:
            client.topggpy = topgg.DBLClient(
                config.DBL.TOKEN, autopost=True, post_shard_count=True
            ).set_data(client)
            client.topgg_webhook = (
                topgg.WebhookManager().set_data(client).endpoint(dbl_endpoint)
            )
        else:
            print("Top.gg integration not found.")

        # Adding Extensions

        for filename in os.listdir("cogs"):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded extension: {filename[:-3]}")

        await client.start(config.BOT_TOKEN)


if __name__ == "__main__":

    asyncio.run(main())
