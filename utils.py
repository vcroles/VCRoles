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

    def str_to_bool(self, s: bytes) -> bool:
        if s.decode("utf-8") == True:
            return True
        return False

    def decode(self, s: bytes) -> str:
        return s.decode("utf-8")

    def guild_add(self, guild_id: int, type=None):
        if type == None:
            # Guild data
            self.r.hset(f"{guild_id}:gd", "tts:enabled", "False")
            self.r.hset(f"{guild_id}:gd", "tts:role", "None")
            self.r.hset(f"{guild_id}:gd", "logging", "None")

            # Linked data
            self.r.hset(f"{guild_id}:linked", "voice", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "stage", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "category", self.dict_to_str({}))
            self.r.hset(
                f"{guild_id}:linked",
                "all",
                self.dict_to_str({"roles": [], "except": []}),
            )
            self.r.hset(f"{guild_id}:linked", "permanent", self.dict_to_str({}))

            # Generator data
            self.r.hset(f"{guild_id}:gen", "cat", "0")
            self.r.hset(f"{guild_id}:gen", "gen_id", "0")
            self.r.hset(
                f"{guild_id}:gen",
                "interface",
                self.dict_to_str({"channel": 0, "msg_id": 0}),
            )
            self.r.hset(f"{guild_id}:gen", "open", self.list_to_str([]))
        elif type == "gen":
            # Generator data
            self.r.hset(f"{guild_id}:gen", "cat", "0")
            self.r.hset(f"{guild_id}:gen", "gen_id", "0")
            self.r.hset(
                f"{guild_id}:gen",
                "interface",
                self.dict_to_str({"channel": 0, "msg_id": 0}),
            )
            self.r.hset(f"{guild_id}:gen", "open", self.list_to_str([]))
        elif type == "gd":
            # Guild data
            self.r.hset(f"{guild_id}:gd", "tts:enabled", "False")
            self.r.hset(f"{guild_id}:gd", "tts:role", "None")
            self.r.hset(f"{guild_id}:gd", "logging", "None")
        elif type == "linked":
            # Linked data
            self.r.hset(f"{guild_id}:linked", "voice", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "stage", self.dict_to_str({}))
            self.r.hset(f"{guild_id}:linked", "category", self.dict_to_str({}))
            self.r.hset(
                f"{guild_id}:linked",
                "all",
                self.dict_to_str({"roles": [], "except": []}),
            )
            self.r.hset(f"{guild_id}:linked", "permanent", self.dict_to_str({}))

        return True

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
            self.guild_add(guild_id, "gd")
            r_data = self.r.hgetall(f"{guild_id}:gd")
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data

    def update_guild_data(self, guild_id: int, data: dict):
        for key in data:
            self.r.hset(f"{guild_id}:gd", key, data[key])

    def get_linked(self, type: str, guild_id: int) -> dict:
        r_data = self.r.hget(f"{guild_id}:linked", type)
        if r_data:
            return self.str_to_dict(r_data)
        else:
            self.guild_add(guild_id, "linked")
            r_data = self.r.hget(f"{guild_id}:linked", type)
            return self.str_to_dict(r_data)

    def update_linked(self, type: str, guild_id: int, data: dict):
        self.r.hset(f"{guild_id}:linked", type, self.dict_to_str(data))

    def get_generator(self, guild_id: int) -> dict:
        r_data = self.r.hgetall(f"{guild_id}:gen")
        if r_data:
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data
        else:
            self.guild_add(guild_id, "gen")

            r_data = self.r.hgetall(f"{guild_id}:gen")
            data = {}
            for key, value in r_data.items():
                data[self.decode(key)] = self.decode(value)
            return data

    def update_generator(self, guild_id: int, data: dict):
        for key in data:
            if key in ["open", "interface"]:
                self.r.hset(f"{guild_id}:gen", key, self.list_to_str(data[key]))
            else:
                self.r.hset(f"{guild_id}:gen", key, data[key])
