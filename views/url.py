import discord

INVITE_URL = "https://discord.com/api/oauth2/authorize?client_id=775025797034541107&permissions=1039166576&scope=bot%20applications.commands"
DISCORD_URL = "https://discord.gg/yHU6qcgNPy"
WEBSITE_URL = "https://www.vcroles.com"
TOPGG_URL = "https://top.gg/bot/775025797034541107"


class Invite(discord.ui.View):
    """
    Send an Invite button
    """

    def __init__(self):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Invite the bot",
                url=INVITE_URL,
            )
        )


class Discord(discord.ui.View):
    """
    Send a Support Server button
    """

    def __init__(self):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Support Server",
                url=DISCORD_URL,
            )
        )


class Website(discord.ui.View):
    """
    Send a Website button
    """

    def __init__(self):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Website",
                url=WEBSITE_URL,
            )
        )


class TopGG(discord.ui.View):
    """
    Send a Top.gg button
    """

    def __init__(self):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Top.gg",
                url=TOPGG_URL,
            )
        )


class Combination(discord.ui.View):
    """
    Send a button with the:
    - Website
    - Invite
    - Support Server
    - Top.gg Link
    """

    def __init__(self):
        super().__init__()

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Website",
                url=WEBSITE_URL,
            )
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Invite the bot",
                url=INVITE_URL,
            )
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Support Server",
                url=DISCORD_URL,
            )
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Top.gg",
                url=TOPGG_URL,
            )
        )
