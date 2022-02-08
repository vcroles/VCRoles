import redis
import json


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

    def decode(self, s: bytes) -> str:
        return s.decode("utf-8")

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
            return {"tts:enabled": "False", "tts:role": "None", "logging": "None"}

    def update_guild_data(self, guild_id: int, data: dict):
        for key in data:
            self.r.hset(f"{guild_id}:gd", key, data[key])

    def get_linked(self, type: str, guild_id: int) -> dict:
        r_data = self.r.hget(f"{guild_id}:linked", type)
        if r_data:
            return self.str_to_dict(r_data)
        else:
            if type != "all":
                return {}
            return {"roles": [], "except": []}

    def update_linked(self, type: str, guild_id: int, data: dict):
        self.r.hset(f"{guild_id}:linked", type, self.dict_to_str(data))

    def get_generator(self, guild_id: int) -> dict:
        r_data = self.r.hgetall(f"{guild_id}:gen")
        if r_data:
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
                if self.decode(key) == "interface":
                    data[key] = self.str_to_list(data[self.decode(key)])
            return data
        else:
            return {
                "cat": "0",
                "gen_id": "0",
                "open": [],
                "interface": {"channel": "0", "msg_id": "0"},
            }

    def update_generator(self, guild_id: int, data: dict):
        for key in data:
            if key in ["open", "interface"]:
                self.r.hset(f"{guild_id}:gen", key, json.dumps(data[key]))
            else:
                self.r.hset(f"{guild_id}:gen", key, data[key])

    def update_gen_open(self, guild_id: int, data: list):
        self.r.hset(f"{guild_id}:gen", "open", self.list_to_str(data))
