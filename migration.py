from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import redis.asyncio as aioredis
from prisma.enums import LinkType
from prisma.types import (
    GuildUpdateInput,
    LinkCreateWithoutRelationsInput,
    VoiceGeneratorCreateWithoutRelationsInput,
)

import config
from utils import DatabaseUtils

db = DatabaseUtils()

ar: aioredis.Redis[Any] = aioredis.Redis(
    host=config.REDIS.HOST,
    password=config.REDIS.PASSWORD,
    port=config.REDIS.PORT,
    db=config.REDIS.DB,
    decode_responses=True,
)


def str_to_bool(val: str) -> bool | None:
    if val == "True":
        return True
    elif val == "False":
        return False
    else:
        return None


def map_type(link_type: str) -> LinkType:
    if link_type == "all":
        return LinkType.ALL
    elif link_type == "category":
        return LinkType.CATEGORY
    elif link_type == "permanent":
        return LinkType.PERMANENT
    elif link_type == "stage":
        return LinkType.STAGE
    elif link_type == "voice":
        return LinkType.REGULAR
    return LinkType.REGULAR


def parse_link_data(
    str_link_type: str, guild_id: str, data: dict[str, dict[str, str | list[str]]]
) -> list[LinkCreateWithoutRelationsInput]:
    if data.get("format"):
        data.pop("format")

    if str_link_type not in ["all", "category", "permanent", "stage", "voice"]:
        return []

    link_type = map_type(str_link_type)

    new_links: list[LinkCreateWithoutRelationsInput] = []

    if link_type != LinkType.ALL:
        for channel_id in data:
            new_link: LinkCreateWithoutRelationsInput = {
                "id": channel_id,
                "type": link_type,
                "guildId": guild_id,
            }

            if data[channel_id].get("roles") and len(data[channel_id]["roles"]) > 0:
                new_link["linkedRoles"] = data[channel_id]["roles"]  # type: ignore
            if (
                data[channel_id].get("reverse_roles")
                and len(data[channel_id]["reverse_roles"]) > 0
            ):
                new_link["reverseLinkedRoles"] = data[channel_id]["reverse_roles"]  # type: ignore
            if (
                data[channel_id].get("speaker_roles")
                and len(data[channel_id]["speaker_roles"]) > 0
            ):
                new_link["speakerRoles"] = data[channel_id]["speaker_roles"]  # type: ignore
            if data[channel_id].get("suffix") and len(data[channel_id]["suffix"]) > 0:
                new_link["suffix"] = data[channel_id]["suffix"]  # type: ignore

            new_links.append(new_link)
    else:
        new_link: LinkCreateWithoutRelationsInput = {
            "id": guild_id,
            "type": link_type,
            "guildId": guild_id,
        }

        if data.get("roles") and len(data["roles"]) > 0:
            new_link["linkedRoles"] = data["roles"]  # type: ignore
        if data.get("reverse_roles") and len(data["reverse_roles"]) > 0:
            new_link["reverseLinkedRoles"] = data["reverse_roles"]  # type: ignore
        if data.get("suffix") and len(data["suffix"]) > 0:
            new_link["suffix"] = data["suffix"]  # type: ignore
        if data.get("except") and len(data["except"]) > 0:
            new_link["excludeChannels"] = data["except"]  # type: ignore

        new_links.append(new_link)

    return new_links


def parse_gen_data(
    guild_id: str, data: dict[Any, Any]
) -> list[VoiceGeneratorCreateWithoutRelationsInput]:
    gen_data: VoiceGeneratorCreateWithoutRelationsInput = {"guildId": guild_id}

    if data.get("open"):
        gen_data["openChannels"] = data["open"]
    if data.get("interface"):
        if data["interface"].get("channel"):
            gen_data["interfaceChannel"] = data["interface"]["channel"]
        if data["interface"].get("msg_id"):
            gen_data["interfaceMessage"] = data["interface"]["msg_id"]
    if data.get("cat"):
        gen_data["categoryId"] = data["cat"]
    if data.get("gen_id"):
        gen_data["generatorId"] = data["gen_id"]

    return [gen_data]


def parse_guild_data(guild_id: str, data: dict[Any, Any]) -> list[GuildUpdateInput]:
    guild_data: GuildUpdateInput = {"id": guild_id}

    if data.get("tts:enabled"):
        guild_data["ttsEnabled"] = str_to_bool(data["tts:enabled"]) or False
    if data.get("tts:role"):
        guild_data["ttsRole"] = data["tts:role"] if data["tts:role"] != "None" else None
    if data.get("tts:leave"):
        guild_data["ttsLeave"] = str_to_bool(data["tts:leave"]) or True
    if data.get("logging"):
        guild_data["logging"] = data["logging"] if data["logging"] != "None" else None

    return [guild_data]


async def main():
    await db.connect()

    await db.db.link.delete_many()
    await db.db.voicegenerator.delete_many()
    await db.db.guild.delete_many()

    linked_keys = await ar.keys("*:linked")
    gen_keys = await ar.keys("*:gen")
    guild_data_keys = await ar.keys("*:gd")

    guild_ids: list[str] = []
    guild_ids.extend([guild.removesuffix(":linked") for guild in linked_keys])
    guild_ids.extend([guild.removesuffix(":gen") for guild in gen_keys])
    guild_ids.extend([guild.removesuffix(":gd") for guild in guild_data_keys])
    guild_ids = list(set(guild_ids))

    await db.db.guild.create_many([{"id": id} for id in guild_ids])

    start_time = time.perf_counter()

    await migrate_guild_data()
    await migrate_linked()
    await migrate_generator()

    print(f"Time taken: {time.perf_counter()-start_time}")

    await db.disconnect()


async def migrate_linked():
    parsed_list: list[LinkCreateWithoutRelationsInput] = []

    linked_keys = await ar.keys("*:linked")

    for guild_key in linked_keys:
        guild_id: str = guild_key.split(":")[0]
        for link_key in await ar.hkeys(guild_key):
            val = await ar.hget(guild_key, link_key)
            if not val:
                continue
            val = json.loads(val)
            parsed = parse_link_data(link_key, guild_id, val)
            parsed_list.extend(parsed)

    await db.db.link.create_many([{**link} for link in parsed_list])


async def migrate_generator():
    parsed_list: list[VoiceGeneratorCreateWithoutRelationsInput] = []

    gen_keys = await ar.keys("*:gen")

    for guild_key in gen_keys:
        guild_id: str = guild_key.split(":")[0]
        val = await ar.hgetall(guild_key)
        if not val:
            continue
        if val.get("open"):
            val["open"] = json.loads(val["open"])
        if val.get("interface"):
            val["interface"] = json.loads(val["interface"])

        parsed = parse_gen_data(guild_id, val)
        parsed_list.extend(parsed)

    await db.db.voicegenerator.create_many([{**gen} for gen in parsed_list])


async def migrate_guild_data():
    parsed_list: list[GuildUpdateInput] = []

    guild_data_keys = await ar.keys("*:gd")

    for guild_key in guild_data_keys:
        guild_id: str = guild_key.split(":")[0]
        val = await ar.hgetall(guild_key)
        if not val:
            continue
        parsed = parse_guild_data(guild_id, val)
        parsed_list.extend(parsed)

    async with db.db.batch_() as batcher:
        for gd in parsed_list:
            batcher.guild.update(where={"id": gd["id"]}, data={**gd})


if __name__ == "__main__":
    asyncio.run(main())
