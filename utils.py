import json

import discord
import redis


class RedisUtils:
    """Tools for interacting with the Redis database & converting datatypes"""

    def __init__(self, r: redis.Redis):
        self.r = r
        self.DATA_FORMAT_VER = 2
        self.DATA_FORMAT = {
            "roles": [],
            "suffix": "",
            "reverse_roles": [],
        }

    def to_str(self, data) -> str:
        """Convert data `dict|list` to JSON `string`"""
        return json.dumps(data)

    def from_str(self, s: str) -> dict:
        """Convert JSON `string` to data `dict|list`"""
        return json.loads(s)

    def _decode(self, s: bytes) -> str:
        """Decode bytes to string"""
        return s.decode("utf-8")

    def guild_remove(self, guild_id: int):
        self.r.delete(f"{guild_id}:gd", f"{guild_id}:linked", f"{guild_id}:gen")

    def get_guild_data(self, guild_id: int) -> dict:
        r_data = self.r.hgetall(f"{guild_id}:gd")
        if r_data:
            data = {}
            for key, value in r_data.items():
                data[self._decode(key)] = self._decode(value)
            return data
        else:
            return {
                "tts:enabled": "False",
                "tts:role": "None",
                "tts:leave": "True",
                "logging": "None",
            }

    def update_guild_data(self, guild_id: int, data: dict):
        for key in data:
            self.r.hset(f"{guild_id}:gd", key, data[key])

    def get_linked(self, type: str, guild_id: int) -> dict:
        r_data = self.r.hget(f"{guild_id}:linked", type)
        if r_data:
            data = self.from_str(self._decode(r_data))

            if type == "all":
                if "suffix" not in data:
                    data["suffix"] = ""
                if "reverse_roles" not in data:
                    data["reverse_roles"] = []
                return data
            # data formats:
            # 0: {channel_id: [role_id, role_id, ...]}
            # 1: {channel_id: {"roles": [role_id, role_id, ...], "suffix": "..."}}
            # 2: {channel_id: {"roles": [role_id, role_id, ...], "suffix": "...", "reverse_roles": [role_id, role_id, ...]}}
            if "format" not in data or data["format"] == 0:
                # reformat data to type 1
                for channel_id, roles in data.items():
                    if isinstance(roles, list):
                        data[channel_id] = {"roles": roles, "suffix": ""}
                data["format"] = 1
                self.update_linked(type, guild_id, data)
            if data["format"] == 1:
                # reformat data to type 2
                for channel_id in data:
                    if channel_id != "format":
                        data[channel_id]["reverse_roles"] = []
                data["format"] = self.DATA_FORMAT_VER
                self.update_linked(type, guild_id, data)
            return data

        else:
            if type == "all":
                return {"roles": [], "except": [], "suffix": "", "reverse_roles": []}
            return {"format": self.DATA_FORMAT_VER}

    def update_linked(self, type: str, guild_id: int, data: dict):
        self.r.hset(f"{guild_id}:linked", type, self.to_str(data))

    def get_generator(self, guild_id: int) -> dict:
        r_data = self.r.hgetall(f"{guild_id}:gen")
        if r_data:
            data = {}
            for key, value in r_data.items():
                data[self._decode(key)] = self._decode(value)
                if self._decode(key) == "interface":
                    data[key] = self.from_str(data[self._decode(key)])
            return data
        else:
            return {
                "cat": "",
                "gen_id": "",
                "open": [],
                "interface": {"channel": "", "msg_id": ""},
            }

    def update_generator(self, guild_id: int, data: dict):
        for key in data:
            if key in ["open", "interface"]:
                self.r.hset(f"{guild_id}:gen", key, json.dumps(data[key]))
            else:
                self.r.hset(f"{guild_id}:gen", key, data[key])

    def update_gen_open(self, guild_id: int, data: list):
        self.r.hset(f"{guild_id}:gen", "open", self.to_str(data))


# Username Suffix Tools


async def add_suffix(member: discord.Member, suffix: str):
    if suffix == "" or member.bot:
        return

    try:
        member = await member.guild.fetch_member(member.id)
        username = member.display_name
        if not username.endswith(suffix):
            username += f" {suffix}"
            await member.edit(nick=username)
    except:
        pass


async def remove_suffix(member: discord.Member, suffix: str):
    if suffix == "" or member.bot:
        return

    try:
        member = await member.guild.fetch_member(member.id)
        username = member.display_name
        if username.endswith(suffix):
            await member.edit(nick=username.removesuffix(suffix))
    except:
        pass


# Unlink commands delete empty channel data


def handle_data_deletion(data: dict, channel_id: str) -> dict:
    if (
        not data[channel_id]["roles"]
        and not data[channel_id]["reverse_roles"]
        and not data[channel_id]["suffix"]
    ):
        data.pop(channel_id)

    return data
