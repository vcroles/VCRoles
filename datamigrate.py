import redis, json, os

r = redis.Redis(host="188.40.130.153", port=6379, db=0, password="sht8RNp@@X5CoEy&")


def dict_to_str(d: dict) -> str:
    return json.dumps(d)


def linked_migrate():

    for filename in os.listdir("old_linked"):
        if filename.endswith(".json"):
            guild_id = filename.removesuffix(".json")

            with open(f"old_linked\\{filename}", "r") as f:
                data = json.load(f)

            r.hset(f"{guild_id}:linked", "voice", dict_to_str(data["voice"]))
            r.hset(f"{guild_id}:linked", "stage", dict_to_str(data["stage"]))
            r.hset(f"{guild_id}:linked", "category", dict_to_str(data["category"]))
            r.hset(f"{guild_id}:linked", "all", dict_to_str(data["all"]))
            r.hset(f"{guild_id}:linked", "permanent", dict_to_str(data["permanent"]))


def guild_data_migrate():

    with open("old_data\\guild_data.json", "r") as f:
        data = json.load(f)

    for id in data:
        r.hset(f"{id}:gd", "tts:enabled", str(data[id]["tts"]["enabled"]))
        r.hset(f"{id}:gd", "tts:role", str(data[id]["tts"]["role"]))
        r.hset(f"{id}:gd", "logging", str(data[id]["logging"]))


def gen_data_migrate():

    with open(f"old_data\\generator.json", "r") as f:
        data = json.load(f)

    for id in data:
        r.hset(f"{id}:gen", "cat", data[id]["cat"])
        r.hset(f"{id}:gen", "gen_id", data[id]["gen_id"])
        r.hset(f"{id}:gen", "open", dict_to_str(data[id]["open"]))
