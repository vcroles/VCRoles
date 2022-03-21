import discord


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
                url="https://discord.com/api/oauth2/authorize?client_id=775025797034541107&permissions=300944400&scope=bot%20applications.commands",
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
                url="https://discord.gg/yHU6qcgNPy",
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
                url="https://www.vcroles.com",
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
                url="https://top.gg/bot/775025797034541107",
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
                url="https://www.vcroles.com",
            )
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Invite the bot",
                url="https://discord.com/api/oauth2/authorize?client_id=775025797034541107&permissions=300944400&scope=bot%20applications.commands",
            )
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Support Server",
                url="https://discord.gg/yHU6qcgNPy",
            )
        )

        self.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.url,
                label="Top.gg",
                url="https://top.gg/bot/775025797034541107",
            )
        )
