import discord

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
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass


async def remove_suffix(member: discord.Member, suffix: str):
    if suffix == "" or member.bot:
        return

    try:
        member = await member.guild.fetch_member(member.id)
        username = member.display_name
        if username.endswith(suffix):
            await member.edit(nick=username.removesuffix(suffix))
    except discord.Forbidden:
        pass
    except discord.HTTPException:
        pass
