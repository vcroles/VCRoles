# VC Roles (Rewrite)

[![Discord Bots](https://top.gg/api/widget/status/775025797034541107.svg)](https://top.gg/bot/775025797034541107)
[![Discord Bots](https://top.gg/api/widget/servers/775025797034541107.svg?noavatar=true)](https://top.gg/bot/775025797034541107)
[![Discord Bots](https://top.gg/api/widget/owner/775025797034541107.svg?noavatar=true)](https://top.gg/bot/775025797034541107)
[![License](https://img.shields.io/badge/license-Apache%202.0%20with%20Commons%20Clause-blue)](https://commonsclause.com/)
[![Pull Requests](https://img.shields.io/badge/Pull%20Requests-Welcome!-brightgreen)](https://github.com/CDESamBotDev/VCRoles/pulls)

VC Roles, TTS & more!

<https://www.vcroles.com>

This is a bot that will make your server and voice channels much more interactive, with the ability to give a user a role when they join a voice channel, remove it when they leave the channel, sending TTS messages into voice channels for those times when you can't speak, creating and managing voice channels and more! This is the bot you need to make your servers more interactive, and to help bring a community together.

## GitHub

VC Roles is open source here, and we welcome any pull requests!

Please note however that this code is intended for educational purposes only, and we will not provide support for self-hosting the bot.

## Development Envrionment

We reccomend using a virtual environment for python. You can do this by:

-   Creating a new virtual environment called env `py -m venv env` or `python3 -m venv env`
-   Activating the virtual environment `.\env\Scripts\activate` or `source env/bin/activate`
-   Install the project dependencies `pip install -r requirements.txt`

## Config Files

To get the bot running, you must configure a number of things.

```py
# /config.py

BOT_TOKEN: str = # the discord bot token
ENVIRONMENT: Literal["DEV", "PROD"] = # how to run the bot (such as whether to use topgg integration)
WEBSERVER_PORT: int = # the port to listen for offline status requests
GUMROAD_PRODUCT_ID: str = # the gumroad product id

class REDIS:
    HOST: str = # the redis host
    PORT: int = # the redis port
    DB: int = # the redis db to use
    PASSWORD: str = # the password to authenticate

class DBL: # dbl (TopGG)
    TOKEN: str = # the dbl token
    WEBHOOK_PASSWORD: str = # the password needed to authenticate
    WEBHOOK_PORT: int = # the port to listen on
```

```properties
# /.env

DATABASE_URL="" # the postgres connection string
```

## Code formatter

Use the ['Black'](https://black.readthedocs.io/en/stable/getting_started.html) python code formatter.

-   Install with: `python -m pip install black` or `pip install black`
-   Run formatter in terminal with: `python -m black .` or `black .`

## Current Library

Now using stable discord.py release `discord.py[voice,speed]`

## Links

### Top.gg

<https://top.gg/bot/775025797034541107>

### Official Website

<https://www.vcroles.com>

### Admin Invite Link

<https://discord.com/api/oauth2/authorize?client_id=775025797034541107&permissions=300944400&scope=bot%20applications.commands>

### Default Invite Link

<https://discord.com/api/oauth2/authorize?client_id=775025797034541107&permissions=300944400&scope=bot%20applications.commands>

[![Discord Bots](https://top.gg/api/widget/775025797034541107.svg)](https://top.gg/bot/775025797034541107)
